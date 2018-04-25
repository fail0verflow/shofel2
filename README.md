# ShofEL2

A misleadingly-named Tegra X1 Boot ROM exploit and Nintendo Switch Linux loader.

See the accompanying blog post: https://fail0verflow.com/blog/2018/shofel2/

## Obligatory disclaimer

If your Switch catches fire or turns into an Ouya, it's not our fault. It's
stupidly easy to blow up embedded platforms like this with bad software (e.g.
all voltages are software-controlled). We already caused temporary damage to one
LCD panel with bad power sequencing code. Seriously, do not complain if
something goes wrong.

On the other hand, this exploit probably works on the Ouya...

## Usage

You need arm-linux-gnueabi and aarch64-linux-gnu toolchains.
[Linaro](https://releases.linaro.org/components/toolchain/binaries/latest-7/)
have working toolchains.

Clone everything:

    $ git clone https://github.com/fail0verflow/shofel2.git
    $ git clone --recursive https://github.com/fail0verflow/switch-coreboot.git coreboot
    $ git clone https://github.com/fail0verflow/switch-u-boot.git u-boot
    $ git clone https://github.com/fail0verflow/switch-linux.git linux
    $ git clone https://github.com/boundarydevices/imx_usb_loader.git

Build the cbfs loader:

    $ cd shofel2/exploit
    $ make

Build u-boot:

    $ cd u-boot
    $ export CROSS_COMPILE=aarch64-linux-gnu-
    $ make nintendo-switch_defconfig
    $ make

Build coreboot:

    $ cd coreboot
    $ make nintendo_switch_defconfig
    $ make iasl
    $ make

Build imx_usb_loader:

    $ cd imx_usb_loader
    $ make

Build Linux:

    $ cd linux
    $ export ARCH=arm64
    $ export CROSS_COMPILE=aarch64-linux-gnu-
    $ make nintendo-switch_defconfig
    $ make

Run the exploit

    $ cd shofel2/exploit
    $ ./shofel2.py cbfs.bin ../../coreboot/build/coreboot.rom

Build the u-boot script and run it

    $ cd shofel2/usb_loader
    $ ../../u-boot/tools/mkimage -A arm64 -T script -C none -n "boot.scr" -d switch.scr switch.scr.img
    $ ../../imx_usb_loader/imx_usb -c .

If all went well, you should have some penguins. You should probably put a root
filesystem on your SD card.
[Arch Linux ARM](http://os.archlinuxarm.org/os/ArchLinuxARM-aarch64-latest.tar.gz)
provides ready-made rootfs tarballs
that you should totally use. Userspace libraries and other patches coming soon.

**You will most likely need a 1.8V serial cable connected to the right hand side
Joy-Con port to do anything useful with this at this point**. Please do not bug
us with questions about how to get this to run if you do not have a means to
debug things yourself. This is not ready for end users. If you really want to
try configuring your Linux image standalone to boot with WiFi or X support
to get something done without a serial console, you're on your own and you get
to suffer through the pain all by yourself. Hint: WiFi is broken on the first
boot, you need to reboot on the first Linux launch (which puts you back into
RCM mode), and then run the exploit again. Patches welcome.
