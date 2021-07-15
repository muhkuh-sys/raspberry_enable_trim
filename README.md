Enable Trim on a Raspberry
==========================

If you are one of the lucky owners of a Raspberry Pi and a SSD you might have heard of TRIM - or better the missing TRIM feature. As I learned from [this](https://www.jeffgeerling.com/blog/2020/enabling-trim-on-external-ssd-on-raspberry-pi) excellent article by Jeff Geerling there is a good chance that it can be enabled with a few commands. You have to look up some numbers and end up with 2 commands specific for your setup (i.e. the combination of SSD plus adapter). They have to be executed after every boot.

Sometimes I have an urge to change components in my setup (like an SSD). Combined with my tendency to forget important dependencies (like hardcoded numbers) I needed a more adaptive solution. The Python script in this repository tries to follow the steps described by Jeff as close as possible. It works for me, but please be careful.

## My setup

I'm using Ubuntu 20.04 with a Kingston A400 drive connected with a "renkforce USB 3.0 to SATA" adapter:

```
muhkuh@flashstation01:~$ lsusb
Bus 002 Device 002: ID 174c:55aa ASMedia Technology Inc. Name: ASM1051E SATA 6Gb/s bridge, ASM1053E SATA 6Gb/s bridge, ASM1153 SATA 3Gb/s bridge, ASM1153E SATA 6Gb/s bridge
...
```

And from dmesg:
```
[    3.909785] usbcore: registered new interface driver usb-storage
[    3.931434] scsi host0: uas
[    3.935473] usbcore: registered new interface driver uas
[    3.936003] scsi 0:0:0:0: Direct-Access     KINGSTON  SA400S37480G    0    PQ: 0 ANSI: 6
[    3.953369] sd 0:0:0:0: Attached scsi generic sg0 type 0
[    3.953955] sd 0:0:0:0: [sda] 937703088 512-byte logical blocks: (480 GB/447 GiB)
[    3.966533] sd 0:0:0:0: [sda] Write Protect is off
[    3.971381] sd 0:0:0:0: [sda] Mode Sense: 43 00 00 00
[    3.975334] sd 0:0:0:0: [sda] Write cache: enabled, read cache: enabled, doesn't support DPO or FUA
[    3.989386] sd 0:0:0:0: [sda] Optimal transfer size 33553920 bytes
```

## How to use

The script has 1 argument, which is the device to activate TRIM for. My SSD appears at ```/dev/sda```, so my device is ```sda``` and I run the script like this:

```
python3 sda
```

The script first checks if TRIM is not yet active. Then it looks up the values and constructs the commands necessary for the activation:
```
muhkuh@flashstation01:~$ sudo python3 trim.py sda
TRIM is not enabled for sda.
Set the provisioning mode in /sys/devices/platform/scb/fd500000.pcie/pci0000:00/0000:00:00.0/0000:01:00.0/usb2/2-2/2-2:1.0/host0/target0:0:0/0:0:0:0/scsi_disk/0:0:0:0/provisioning_mode to "unmap".
Setting the maximum number of bytes to discard in /sys/class/block/sda/queue/discard_max_bytes to 2147450880

muhkuh@flashstation01:~$ sudo python3 trim.py sda
TRIM is enabled for sda.
```

There is also a service file for systemd to automate the start. Replace the ```ENTER_DEVICE_HERE``` part in ```enable_trim.service```  with your device and copy it to one of the folders with service files, for example ```/etc/systemd/system```. Copy the script ```trim.py``` to ```/usr/local/bin/``` and enable the script:

```
sudo systemctl enable enable_trim.service
```

After a reboot TRIM should be active. Check it with...
```
muhkuh@flashstation01:~$ systemctl status enable_trim.service
● enable_trim.service - Activate TRIM for SSD
     Loaded: loaded (/etc/systemd/system/enable_trim.service; enabled; vendor preset: enabled)
     Active: active (exited) since Thu 2021-07-15 23:42:55 CEST; 45s ago
    Process: 1496 ExecStart=/usr/bin/python3 /usr/local/bin/trim.py sda (code=exited, status=0/SUCCESS)
   Main PID: 1496 (code=exited, status=0/SUCCESS)

Jul 15 23:42:55 flashstation01 systemd[1]: Starting Activate TRIM for SSD...
Jul 15 23:42:55 flashstation01 python3[1496]: TRIM is not enabled for sda.
Jul 15 23:42:55 flashstation01 python3[1496]: Set the provisioning mode in /sys/devices/platform/scb/fd500000.pcie/pci0000:00/0000:00:00.0/0000:01:00.0/usb2/2-2/2-2:1.0/host0/target0:0:0/0:0:0:0/scsi_di>
Jul 15 23:42:55 flashstation01 python3[1496]: Setting the maximum number of bytes to discard in /sys/class/block/sda/queue/discard_max_bytes to 2147450880
Jul 15 23:42:55 flashstation01 systemd[1]: Finished Activate TRIM for SSD.
```

Finally a ```sudo systemctl enable fstrim.timer``` enables automatic trimming.
