This is a camera that's been a long time coming. As far as I know, there's nothing quite like it out there. 

**This is the Custom PCB version - it's a little more compact, but requires a custom PCB order. KiCAD and Gerber files are provided. There's no build guide specific to this version, but I'm going to assume if you're considering this version you'll be able to figure it out.**

**There's also a connector for a linear slide potentiometer on the PCB and an optional lens assembly STEP file that uses this instead of an optical sensor to measure lens extension, but I never took it further than that, so there's not code for this - and I never tested it in practice. It's there if you want to try it, though.** 

The LRF45 is a mostly 3D-printed camera with a LiDAR-powered digital rangefinder that is electronically coupled to a sensor that reads the lens extension. Which makes this a lens-coupled, hand-held large-format rangefinder. It also has a built-in light meter!

- It is designed for the Fujinon-W 105mm f5.6
- It is compatible with any Graflok film back, even the Lomograflok with some caveats
- The electronics are freely available, affordable, and easy to find
- The viewfinder optics and lens proper are the most expensive parts of this camera, and even those are relatively affordable and easy to procure
- The source code that powers the electronics and rangefinder (as well as light-meter) is open-source and can be found on Github
- There's a detailed build guide in PDF format below
- There's an OrcaSlicer file with all the hard work done for you, but if you want to slice it yourself, all the 3MFs are available as seperate files
- I also provide a STEP file with all the parts if you want to modify or remix the camera to use it with different lenses or formats

I really hope someone out there attempts to build this, and shoot with it. I want to see your makes, as well as your photos!
I have a few example photos on Instagram:

https://www.instagram.com/p/C1C5XITI7D1/
https://www.instagram.com/p/C1MwscKobC5/
https://www.instagram.com/p/C1XakoNo_7q/
https://www.instagram.com/p/C1zOQ6SIrhM/

The light leak in the first three posts has been fixed in the release version.