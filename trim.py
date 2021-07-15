#! /usr/bin/python3
import argparse
import json
import os
import re
import shutil
import stat
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("device", help="The device to enable trim on. Example: sda")
args = parser.parse_args()

# TODO: select the disk somehow...
strDevice = args.device
strDevicePath = os.path.join('/dev', strDevice)

# Test if all commands are present.
atCmd = {}
astrRequiredCommands = [
    'lsblk',
    'sg_vpd',
    'sg_readcap'
]
for strCmd in astrRequiredCommands:
    strPath = shutil.which(strCmd)
    if strPath is None:
        raise Exception(
            'The required command %s was not found in the path.' % strCmd
        )
    atCmd[strCmd] = strPath

# ----------------------------------------------------------------------------
# -
# - Get the block numbers for the device.
# -
tStat = os.stat(strDevicePath)
if stat.S_ISBLK(tStat.st_mode) == 0:
    raise Exception(
        'The path %s does not point to a block device.' % strDevicePath
    )
strSysBlockLink = os.path.join('/sys/class/block', strDevice)
if os.path.islink(strSysBlockLink) is not True:
    raise Exception(
        'The path %s is not a link.' % strSysBlockLink
    )
strSysBlockPath = os.readlink(strSysBlockLink)
# Make sure the result is an absolute path.
strSysBlockPath = os.path.abspath(
    os.path.join(
        os.path.dirname(strSysBlockLink),
        strSysBlockPath
    )
)


# ----------------------------------------------------------------------------
# -
# - Run lsblk to get the discard capabilities of the device.
# - If the "disc-max" value of the device is "0B" then TRIM is not enabled.
# -

# Check if trim is currently active.
strOutput = subprocess.check_output(
    [atCmd['lsblk'], '--json', '--discard', strDevicePath],
    stderr=subprocess.STDOUT
)
tOutput = json.loads(strOutput)

# Search the device in the list of blockdevices.
tBlockDevice = None
for tB in iter(tOutput['blockdevices']):
    if tB['name'] == strDevice:
        tBlockDevice = tB
        break
if tBlockDevice is None:
    raise Exception(
        'Failed to find device %s in the output of lsblk.' % strDevice
    )
strDiscMax = tBlockDevice['disc-max']
if strDiscMax != '0B':
    print('TRIM is enabled for %s.' % strDevice)
else:
    print('TRIM is not enabled for %s.' % strDevice)

    # ------------------------------------------------------------------------
    # -
    # - Check if the firmware supports TRIM.
    # -
    strOutput = subprocess.check_output(
        [atCmd['sg_vpd'], '-p', 'lbpv', strDevicePath],
        stderr=subprocess.STDOUT
    ).decode(
        'utf-8',
        'replace'
    )
    tMatch = re.search(
        r'^\s+Unmap command supported \(LBPU\): (\d+)$',
        strOutput,
        re.MULTILINE
    )
    if tMatch is None:
        raise Exception(
            'Failed to get the state of the unmap command support.'
        )
    ulUnmapCommandSupported = int(tMatch.group(1))

    if ulUnmapCommandSupported == 0:
        raise Exception('The firmware does not support TRIM.')

    # ------------------------------------------------------------------------
    # -
    # - Get the parameter to enable TRIM.
    # -
    strOutput = subprocess.check_output(
        [atCmd['sg_vpd'], '-p', 'bl', strDevicePath],
        stderr=subprocess.STDOUT
    ).decode(
        'utf-8',
        'replace'
    )
    # Get the maximum unmap LBA count.
    tMatch = re.search(
        r'^\s+Maximum unmap LBA count: (\d+)$',
        strOutput,
        re.MULTILINE
    )
    if tMatch is None:
        raise Exception('Failed to get maximum unmap LBA count.')
    ulMaxUnmapLBACount = int(tMatch.group(1))
    # Get the maximum unmap block descriptor count.
    tMatch = re.search(
        r'^\s+Maximum unmap block descriptor count: (\d+)$',
        strOutput,
        re.MULTILINE
    )
    if tMatch is None:
        raise Exception(
            'Failed to get the maximum unmap block descriptor count.'
        )
    ulMaxUnmapBlockDescriptorCount = int(tMatch.group(1))

    strOutput = subprocess.check_output(
        [atCmd['sg_readcap'], '-l', strDevicePath],
        stderr=subprocess.STDOUT
    ).decode(
        'utf-8',
        'replace'
    )
    tMatch = re.search(
        r'^\s+Logical block length=(\d+) bytes$',
        strOutput,
        re.MULTILINE
    )
    if tMatch is None:
        raise Exception(
            'Failed to get the logical block length of the device.'
        )
    ulLogicalBlockLength = int(tMatch.group(1))

    strSysDevicePath = os.path.abspath(
        os.path.join(
            strSysBlockPath,
            '..',
            '..',
            'scsi_disk'
        )
    )
    if os.path.isdir(strSysDevicePath) is not True:
        raise Exception(
            'The path %s does not exist.' % strSysDevicePath
        )
    astrPMFiles = []
    for strPath, astrDirNames, astrFileNames in os.walk(strSysDevicePath):
        if 'provisioning_mode' in astrFileNames:
            astrPMFiles.append(
                os.path.join(strPath, 'provisioning_mode')
            )
    if len(astrPMFiles) == 0:
        raise Exception(
            'No provisioning_mode files found below %s.' % strSysDevicePath
        )

    for strPath in astrPMFiles:
        tFile = open(strPath, 'rt')
        strMode = tFile.read()
        tFile.close()
        if strMode == 'full\n':
            print('Set the provisioning mode in %s to "unmap".' % strPath)
            tFile = open(strPath, 'wt')
            tFile.write('unmap\n')
            tFile.close()
        elif strMode == 'unmap\n':
            print(
                'The provisioning mode in %s is already set to "unmap".' %
                strPath
            )
        else:
            raise Exception(
                'Invalid provisioning mode in %s: %s' % (strPath, strMode)
            )

    ulDiscardMaxBytes = ulMaxUnmapLBACount*ulLogicalBlockLength
    strPath = os.path.join(
        strSysBlockLink,
        'queue',
        'discard_max_bytes'
    )
    if os.path.isfile(strPath) is not True:
        raise Exception(
            'The path %s does not exist.' % strPath
        )
    print(
        'Setting the maximum number of bytes to discard in %s to %d' % (
            strPath,
            ulDiscardMaxBytes
        )
    )
    tFile = open(strPath, 'wt')
    tFile.write('%d\n' % ulDiscardMaxBytes)
    tFile.close()
