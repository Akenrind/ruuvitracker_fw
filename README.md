# RuuviTracker with [MicroPython][upy]

RuuviTracker firmware is based on MicroPython, an MIT-licensed implementation of the Python 3 programming language that is optimised to run on a microcontroller.

## Getting set up

### Dependencies

In order to begin, you must have these dependencies installed on your system.

**NOTE**: [stlink](https://github.com/texane/stlink) can't be installed via package managers.

#### Quick guide

##### **Debian**:

`sudo apt-get install git dfu-util gcc-arm-none-eabi libusb-dev screen build-essential openocd autoconf dosfstools rsync`

##### **Ubuntu**:

<https://kirjoitusalusta.fi/ruuvitracker-ubuntu1404>

##### **Fedora** (not tested yet):

`sudo yum install git dfu-util arm-none-eabi-gcc libusb-devel screen make automake gcc gcc-c++ kernel-devel openocd dosfstools rsync`

##### **Windows**:

Currently, flashing is only supported on UNIX-like systems, such as Linux and OS X. If you are a Windows user, refer to this virtual machine related setup: <https://kirjoitusalusta.fi/ruuvitracker-ubuntu1404> 

##### Others:

Install from source what you can't obtain via package managers.

#### Complete list

* [git](https://git-scm.com/)

* [dfu-util](http://dfu-util.sourceforge.net/), USB Device Firmware Upgrade tool

* [GCC ARM Embedded toolchain](https://launchpad.net/gcc-arm-embedded/+download) or other cross-compiler (e.g. gcc-arm-none-eabi)

* [openocd](http://openocd.org/), Free and Open On-Chip Debugging utility

* [stlink](https://github.com/texane/stlink), stm32 discovery line linux programmer

* [libusb-dev](http://www.libusb.org/), USB developer library

* [autoconf](http://www.gnu.org/software/autoconf/autoconf.html)

* **build-essential**, essential build tools

* [screen](https://www.gnu.org/software/screen/), an application which allows you to run programs in a console section

### Recommended Utilities

* [rsync](https://rsync.samba.org/), provides fast incremental file transfer

* [dosfstools](https://github.com/dosfstools/dosfstools), for creating, checking and labeling file systems of the FAT family

(You will need `fsck.fat` for dirty bit removal if the device is not properly unmounted.)

### Building

NOTE: Building requires a proper git clone, we use submodules and you must be able to init/update them too.

Building is simple, run `./ruuvi_build.sh`

If you want to build for a different board than RUUVITRACKER_C3 (which is revC2 compatible if you happen to have C2) run `BOARD=MYBOARD ./ruuvi_build.sh`,
in this case you must have your board files in the standard location under `stmhal/boards/`.

## Flashing == Installing

### 1. Enter bootloader state
The device must be in bootloader state in order to receive firmware code.
There's a small switch on the board that you must hold down while plugging in the external power source.

1) Hold down the switch on the board while plugging in the external power source.

2) Plug the device into your PC via microUSB cable, the switch may now be released.

3) Run `ruuvi_program.sh`, this will look for compiled firmware and install the "best". You may need root privileges.

### 2. Reset

Do a hardware reset. This is done by unplugging both the external power source and USB cable for a while.

## Using

Connect the power source and USB cable to get the serial terminal and board flash-drive.

If the flashing steps were correctly carried out, your operating system will be able to detect and mount the device.

## Using

Connect the power source and USB cable to get the serial terminal and board flash-drive.

If the flashing steps were correctly carried out, your operating system will be able to detect and mount the device.

See [MicroPython documentation](http://docs.micropython.org/en/latest/) for details about execution environment.

TODO: Document the board specific python modules via [gh-pages](https://pages.github.com/) as they get more functionality.

### REPL quickstart

On Linux the REPL is on ACM device, `/dev/ttyACM0` if you don't have any other CDC serial ports.
(NOTE: You may need sudo rights to execute `screen /dev/ttyACM0`.)

On OSX it's on `/dev/tty.usbmodemXXXX` (exact number is probably board specific).

Copy the files & directories under `stmhal/boards/RUUVITRACKER_C3/copy_to_board` to the board flash-drive.

`cp -r stmhal/boards/RUUVITRACKER_C3/copy_to_board/* /device/mountpoint/`

See 'Tips' for rsync utility.

## Hardware

Schematics, datasheets and other hardware related references are in the [ruuvitracker_hw](https://github.com/RuuviTracker/ruuvitracker_hw/tree/revC3) -repo.

## Testing

Via console, run `*_test.py` scripts under the scripts folder (import <source>, copy-paste, execfile(), or so.)

## Tips

* `screen` output can be logged with the `-L` option. Log will be saved in `screenlog.X` file.

* You may use `rsync` for copying in the code:

`rsync -avzh --progress --delete --include='*.py' --exclude '*' /path/to/stmhal/boards/RUUVITRACKER_C3/copy_to_board/* /mountpointof/PYBFLASH`

* If you have excluded (and deleted) board files because of compactness, you may run `./ignore_deleted.sh` for commits

## Handle problems

### General

* Linux users: make sure your [udev rules](https://wiki.archlinux.org/index.php/Udev) are alright

* Check your USB 1 and USB 2 drivers (bootloader uses the latter)

* Check for damaged connectors

### SIM is locked.

Unlock SIM pin and switch off SIM PIN query with a cell phone (recommended).

(There's also an `unlock_sim.py` script, but don't use it, unless you are inevitably restricted to do so...)

### The file system will not mount.

* Check system log `dmesg | tail` for details

* In order to remove dirty bit, run `fsck.vfat -a /dev/sdX # Device here`

### Software is broken. / Can't exit loops.

Refer to [MicroPython reset procedures](https://micropython.org/doc/tut-reset).

You may need to re-flash the software back in.

### The flash storage is full.

* `rm -rI .Trash-1000` directory on Pyboard

* `rm -r ._* .DS_Store` (OS X resource forks)

* `ls -a` and remove redundant files

* Remember to exclude everything except '*.py'-files with rsync

* Re-write all files (remember backups)

* Refer to "The file system will not mount" (storage can be smaller because of corrupt sectors)

* TODO: uPython C modules, we are seriously running out of space

### Scripts using GSM module crash.

TODO: Possible hardware failures?

[upy]: http://micropython.org/