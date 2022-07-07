#!/usr/bin/python

import sys
import re

def usage():
    print('Usage: `pd-gui-parser [--ptr-len 8[,16]] file [other files ... ]`')
    return -1

def main(argv):
    if not len(argv):
        return usage()
    n = 0
    ptrLen = [8, 16]
    while n < len(argv):
        if '--ptr-len' == argv[n]:
            n = n + 1
            if len(argv) < n + 1:
                return usage()
            arr = argv[n].split(',')
            i0 = int(arr[0])
            if 1 == len(arr):
                i1 = i0
            elif 2 == len(arr):
                i1 = int(arr[1])
            else:
                return usage()
            ptrLen = [i0, i1]
        else:
            break
        n = n + 1
    ret = 0
    # translate each file
    for idx in range(n, len(argv)):
        inFileName = argv[idx]
        with open(inFileName) as file:
            ifile = iter(file)
            out = []
            dic = {}
            dicId = 0
            lappendCount = 0
            for line in ifile:
                line = line.strip()
                guiLineSignature = '^>>'
                res = re.search(guiLineSignature, line)
                if not res:
                    continue # ignore non-GUI line
                # remove signature
                line = re.sub(guiLineSignature, '', line).strip()
                if line == "pdtk_ping":
                    continue # ignore these lines as they may occur at random times
                if re.search('^lappend ::tmp_path {', line):
                    lappendCount = lappendCount + 1
                    if 5 == lappendCount:
                        # the fifth entry normally is the extra/ folder that is
                        # relative to the path of the executable. Ignore it
                        if re.search('^lappend ::tmp_path {.*/extra}', line):
                            continue
                # TODO: we should do some heuristics on ptr len to ensure we
                # use consistent ptr lengths across lines and avoid false positives
                regex = '[0-9a-f]{%d,%d}' % (ptrLen[0], ptrLen[1])
                res = re.findall(regex, line)
                for el in res:
                    if el not in dic:
                        dic[el] = '_%05d_' % dicId
                        dicId = dicId + 1 
                    # translate the string
                    line = re.sub(el, dic[el], line)
                out.append(line)
        if not len(out) or not dicId:
            print('No valid lines or pointers found in', inFileName)
            ret = 1
        outFileName = '%s-tr' % inFileName
        print('Writing to %s' % outFileName)
        with open(outFileName, 'w') as outFile:
            for line in out:
                outFile.write(line + '\n')
    return ret

if __name__ == "__main__":
   ret = main(sys.argv[1:])
   sys.exit(ret)
