#!/usr/bin/python

import sys
import os
import subprocess
import tempfile
import shutil
import re

class CustomException(Exception):
    """ My custom exception"""

def runAndHandle(command):
    cmdStr = "'%s'" % "' '".join(command)
    print('run `%s`' % cmdStr)
    result = subprocess.run(command, shell=False, capture_output=True, encoding='UTF-8')
    if result.returncode:
        raise CustomException('Command %s failed\nSTDOUT:\n%s\nSTDERR:\n%s\n' % (cmdStr, result.stdout, result.stderr))
    return result

def usage():
    print('Usage: `[opts] [pd-binaries] [pd args]`')
    return -1

def main(argv):
    try:
        if len(argv) < 3:
            return usage()
        runPd = True
        ptrLen = False
        tmpDir = False
        keepGoing = False
        userProvidedTmpDir = False
        count = 1
        checkLog = False
        checkSvg = False
        n = 0
        while n < len(argv):
            if '--help' == argv[n] or '-h' == argv[n]:
                usage()
                return 0
            elif '--no-pd' == argv[n]:
                # don't run the Pd stage. Use cached files. It only makes sense if
                # you have specified an existing tmp folder with --tmp
                runPd = False;
            elif '--tmp' == argv[n]:
                n = n + 1
                if len(argv) < n + 1:
                    return usage()
                tmpDir = argv[n]
                userProvidedTmpDir = True
            elif '--count' == argv[n]:
                n = n + 1
                if len(argv) < n + 1:
                    return usage()
                count = int(argv[n])
            elif '--log' == argv[n]:
                checkLog = True
            elif '--svg' == argv[n]:
                checkSvg = True
            elif '--ptr-len' == argv[n]:
                # TODO: automatically forward some options to pd-gui-parser
                n = n + 1
                if len(argv) < n + 1:
                    return usage()
                ptrLen = argv[n]
            else:
                break
            n = n + 1
        if len(argv) < n + 2:
            return usage()
        # follows a list of Pd binaries
        pds = []
        while n in range(n, len(argv)):
            if '-' == argv[n].strip()[0]:
                break
            pds.append(argv[n])
            n = n + 1
        pdArgsInit = []
        #ensure we print GUI debugging
        pdArgsInit = [ '-d', '1' ]
        # everything else are arguments to Pd
        for n in range(n, len(argv)): # one of these will be the test patch (if any)
            pdArgsInit.append(argv[n])

        pathname = os.path.dirname(sys.argv[0])
        pdGuiParser = os.path.abspath(pathname) + '/pd-gui-parser'
        if not tmpDir:
            tmpDir = tempfile.mkdtemp() # TODO: avoid creating if `--tmp` is passed
        pdOutFileNames = []
        retVal = 0
        # go through all instances of Pd
        for c in range(0, count):
            for b in range(0, len(pds)):
                outFileName = tmpDir + '/pd-gui-tester-%d' % b
                if 1 != count:
                    outFileName = outFileName + '-%d' % c
                pdOutFileNames.append(outFileName)
                pdArgs = []
                for n in range(len(pdArgsInit)):
                    pdArgs.append(re.sub('{}', outFileName, pdArgsInit[n]))
                if runPd:
                    command = [ pds[b] ] + pdArgs
                    ret = runAndHandle(command)
                    with open(outFileName, 'w') as outFile:
                        outFile.write(ret.stderr)
                # translate outputs so that they are pointer-independent
                command = ['python3', pdGuiParser ]
                if ptrLen:
                    command = command + [ '--ptr-len', ptrLen ]
                files = []
                if checkLog:
                    files.append(outFileName)
                if checkSvg:
                    files.append(outFileName + '.svg')
                command = command + [ outFileName ]
                ret = runAndHandle(command)
                print(ret.stdout)
                # the first execution is taken as a reference.
                # after that, we compare each execution with that one
                if b != 0 or c != 0:
                    # diff against the original
                    if checkLog:
                        totalTests = totalTests + 1
                        refTrName = pdOutFileNames[0] + '-tr'
                        trName = outFileName + '-tr'
                        ret = runAndHandle(['diff', refTrName, trName])
                        successfulTests = successfulTests + 1
                    if checkSvg:
                        totalTests = totalTests + 1
                        refTrName = pdOutFileNames[0] + '.svg-tr'
                        trName = outFileName + '.svg-tr'
                        ret = runAndHandle(['diff', refTrName, trName])
                        successfulTests = successfulTests + 1
        print("All good")
        if not userProvidedTmpDir:
            shutil.rmtree(tmpDir) # leak temp folder in case of exception so files can be inspected
        return 0
    except CustomException as e:
        print("Error:", e)
        return 1

if __name__ == "__main__":
    ret = main(sys.argv[1:])
    sys.exit(ret)

