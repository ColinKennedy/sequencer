A convenience class to help deal with different type of files sequences 
(files, images, UDIM images, image tiles, etc).

Sequences can be written in multiple ways

Maya: '/some/thing.<f>.tif'
Nuke: '/some/thing.####.tif' or '/some/thing.%04d.tif'
Houdini: '/some/thing.$F4.tif'

To make matters worse, some sequences have special rules, like UDIMs, which
are two dimensional. There are also different UDIM standards, to make matters
worse.

Mari: '/some/thing.1001.tif'
Zbrush: '/some/thing_u0_v0.tif'  # Base zero
Mudbox: '/some/thing_u1_v1.tif'  # Base one

This repository is meant to deal with these variations and make dealing with
sequences a little easier.

Note:
	It's not important to this repository that sequences or files exist, or
	even be valid file paths. As long as a sequence can be written as a string,
	it can be represented in these helper classes.

WIP repository. Check coverage of unittests before use.



