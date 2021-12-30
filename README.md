# python-slamtec-mapper

This repository contains Python code to connect to a Slamtec Mapper. It was tested with a Slamtec Mapper M1M1, but should
theoretically work as well M2M2 or other Slamware based Lidar products that support network communication. It's good
enough to capture laser scanner data and a lot of other infos from the device for further processing or visualisation, but it's not a
full-fledged Python library. It doesn't require the Slamtec SDK to be installed, which allows it to be way more portable
and lightweight.

It was developed by capturing the request that the Slamtec Robo Studio is sending to the device. The protocol is based
on JSON messages sent over port 1445, which are very easy to read. map_data and laser_points are compressed with
a [Run-length encoding (RLE) algorithm](https://en.wikipedia.org/wiki/Run-length_encoding), a decoding function is in
the code.

The `dev_server.py` runs a TCP server that simulates a Lidar device by replaying a valid answer for each command from
the files stored in `test_data/`. Its main purpose is to speed up the software development, because you don’t need to
have the device running. The SlamtecMapper class has a dump argument that allows you to capture your own test data.

**Note:** I've finished my project, so you can't expect any further development of the code. But if you have any
questions, feel free to open an issue here on Github.

One last tip: The device has a web interface (Default: http://192.168.11.1, user admin, password admin111). You can
change the network configuration and passwords there.
