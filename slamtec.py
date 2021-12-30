#!/usr/bin/python3
import socket
import json
import base64
import math
from pprint import pprint
from pathlib import Path
import struct
import time
import sys


class SlamtecMapper:
    def __init__(self, host, port, dump=False, dump_dir="dump"):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((host, port))
        self.request_id = 0
        self.dump = dump
        if self.dump:
            self.dump_dir = Path(f"{dump_dir}/{int(time.time())}/")
            self.dump_dir.mkdir(parents=True)
        else:
            self.dump_dir = None

    def disconnect(self):
        self.socket.close()

    def _send_request(self, command, args=None):
        request = {
            "command": command,
            "args": args,
            "request_id": self.request_id
        }
        self.request_id += 1
        data = json.dumps(request)
        # print("Sent:     {}".format(data))
        if self.dump:
            p = Path(f"{self.dump_dir}/{request['command']}-request.json")
            p.write_text(json.dumps(request, indent=2))

        data_ascii = [ord(character) for character in data]
        data_ascii.extend([10, 13, 10, 13, 10])

        # Connect to server and send data
        self.socket.sendall(bytearray(data_ascii))
        received = b""
        while True:
            size = 1024
            # Receive data from the server and shut down
            response = self.socket.recv(size)

            received += response
            if response[-4:] == b"\r\n\r\n":
                break

        received = received.decode("utf-8")
        received_json = json.loads(received)
        if type(received_json["result"]) == str:
            received_json["result"] = json.loads(received_json["result"])

        if self.dump:
            p = Path(f"{self.dump_dir}/{request['command']}-response.json")
            p.write_text(json.dumps(received_json, indent=2))

        if received_json["request_id"] != request["request_id"]:
            print("wrong request_id in response (%s != %s)" % (received_json["request_id"], request["request_id"]))
            print(received_json)
            return False
        if "code" in received_json["result"] and received_json["result"]["code"] != 1:
            print(received_json["result"].keys())
            print("command %s failed" % command)
            print(received_json)
            return False
        return received_json["result"]

    def get_known_area(self):
        # {"args":{"kind":0,"partially":false,"type":0},"command":"getknownarea","request_id":726532096}
        response = self._send_request(command="getknownarea", args={"kind": 0, "partially": False, "type": 0})
        return response

    def get_pose(self):
        response = self._send_request(command="getpose")
        return response

    def get_map_data(self):
        # {"args":{"area":{"height":3.750,"width":10.55000019073486,"x":-2.899999856948853,"y":-2.599999904632568},"kind":0,"partially":false,"type":0},"command":"getmapdata","request_id":3539992577}
        known_area = self.get_known_area()
        args = {
            "area": {"height": known_area["max_y"] - known_area["min_y"],
                     "width": known_area["max_x"] - known_area["min_x"],
                     "x": known_area["min_x"],
                     "y": known_area["min_y"]},
            "kind": 0,
            "partially": False,
            "type": 0
        }
        response = self._send_request(command="getmapdata", args=args)
        decompressed = self._decompress_rle(response["map_data"])

        pos = 0
        line = 1
        data_2d = {}
        while pos < len(decompressed):
            if line not in data_2d:
                data_2d[line] = []
            data_2d[line].append(decompressed[pos])

            if (pos + 1) % response['dimension_x'] == 0:
                # print(line, data_2d[line])
                line += 1
            pos += 1
        # print(line, data_2d[line])
        response["map_data"] = data_2d
        return response

    def _decompress_rle(self, b64_encoded):
        rle = base64.b64decode(b64_encoded)
        if rle[0:3] != b"RLE":
            print("wrong header %s" % str(rle[0:3]))
            return
        sentinel_list = [rle[3], rle[4]]

        # print("Sentinel list: %s" % sentinel_list)
        pos = 9
        decompressed = []
        while pos < len(rle):
            b = rle[pos]
            # print(b, end=", ")
            if b == sentinel_list[0]:
                # print("sentinel %i, next %i -> %i" % (sentinel_list[0], rle[pos+1], rle[pos+2] ), end=" - ")
                if rle[pos + 1] == 0 and rle[pos + 2] == sentinel_list[1]:
                    sentinel_list.reverse()
                    # print("new sentinel %s" % sentinel_list[0])
                    pos += 2
                else:
                    more = [rle[pos + 2] for i in range(rle[pos + 1])]
                    # print("adding %i" % len(more), end=" - ")
                    decompressed.extend(more)
                    pos += 2
                # break
                # print("")
            else:
                decompressed.append(b)
            pos += 1
        return decompressed

    def get_laser_scan(self, valid_only=False):
        response = self._send_request(command="getlaserscan")
        decompressed = bytearray(self._decompress_rle(response["laser_points"]))

        pos = 0
        bytes_per_row = 12
        data = []
        while pos < len(decompressed):
            parts = struct.unpack("f f h h", decompressed[pos:pos + bytes_per_row])
            pos += bytes_per_row
            distance = parts[0]
            angle_radian = parts[1]
            # todo: decode the remaining bytes
            if distance == 100000.0:
                if valid_only:
                    continue
                valid = False
            else:
                valid = True
            # print(f"distance: {distance:.4f}m, angle {math.degrees(angle_radian):.2f}°, valid {valid}")
            data.append((angle_radian, distance, valid))
            pos += bytes_per_row

        return data

    def get_update(self):
        request = {"args": {"kind": 0}, "command": "getupdate", "request_id": 1651574155}

    def get_localization(self):
        return self._send_request(command="getlocalization")

    def get_current_action(self):
        return self._send_request(command="getcurrentaction")

    def get_robot_config(self):
        return self._send_request(command="getrobotconfig")

    def get_binary_config(self):
        return self._send_request(command="getbinaryconfig")

    def get_robot_features_info(self):
        return self._send_request(command="getrobotfeaturesinfo")

    def get_sdp_version(self):
        return self._send_request(command="getsdpversion")

    def get_device_info(self):
        return self._send_request(command="getdeviceinfo")

    def set_localization(self, state):
        # True: localization on
        # False: localization off
        response = self._send_request(command="setlocalization", args={"value": state})
        # -> {"command":"setlocalization","request_id":1722096331,"result":{"code":1,"timestamp":4925591}}

    def set_update(self, state):
        response = self._send_request(command="setupdate", args={"kind": 0, "value": state})
        # -> {"command":"setupdate","request_id":1722207937,"result":{"code":1,"timestamp":5751061}}

    def clear_map(self):
        response = self._send_request(command="clearmap", args=0)
        # -> {"command":"clearmap","request_id":1722209408,"result":{"code":1,"timestamp":5761982}}

    def get_all(self):
        self.get_known_area()
        self.get_pose()
        self.get_map_data()
        self.get_laser_scan()
        self.get_localization()
        self.get_current_action()
        self.get_robot_config()
        self.get_binary_config()
        self.get_robot_features_info()
        self.get_sdp_version()
        self.get_device_info()


def show_summary(st):
    print("Fetching Map Info...")
    known_area = st.get_known_area()
    map_data = st.get_map_data()
    print(
        f"> Map Area: ({known_area['min_x']:.4f},{known_area['min_y']:.4f},{known_area['max_x']:.4f},{known_area['max_y']:.4f})")
    print(f"> Cell Dimension: ({map_data['dimension_x']}, {map_data['dimension_y']})")
    print(f"> Cell Resolution: ({map_data['resolution']:.4f}, {map_data['resolution']:.4f})")
    print(
        f"> Cell Dimension: ({map_data['dimension_x'] * map_data['resolution']:.2f}m, {map_data['dimension_y'] * map_data['resolution']:.2f}m)")

    print("Fetching Localization Info...")
    pose = st.get_pose()
    print(f"> Position: (x {pose['x']:.4f},y {pose['y']:.4f}, z{pose['z']:.4f})")
    print(f"> Heading: {pose['yaw'] * 180.0 / math.pi:.4f}°")


def show_map(map_data):
    from PIL import Image
    scale = 4
    img = Image.new('L', (map_data['dimension_x'], map_data['dimension_y']), "black")
    pixels = img.load()
    for x in range(img.size[1]):
        for y in range(img.size[0]):
            value = map_data["map_data"][map_data['dimension_y'] - x][y]
            pixels[y, x] = value  # 0-255

    scaled_img = img.resize((map_data['dimension_x'] * scale, map_data['dimension_y'] * scale), Image.ANTIALIAS)
    scaled_img.show()


if __name__ == '__main__':
    # host = "192.168.11.1"
    host = "192.168.123.234"
    st = SlamtecMapper(host=host, port=1445, dump=True)
    # show_summary(st)

    data = st.get_laser_scan(valid_only=False)
    csv = []
    for angle, distance, valid in data:
        csv.append(f"{angle},{distance},{math.degrees(angle)}")
    p = Path("../../laser-full.csv")
    p.write_text("\n".join(csv))
    """
    # st.get_all()
    map_data = st.get_map_data()
    show_map(map_data)
    """
    if "--clear-map" in sys.argv:
        st.clear_map()
    if "--stop-update" in sys.argv:
        st.set_update(False)
    if "--start-update" in sys.argv:
        st.set_update(True)

    st.disconnect()
