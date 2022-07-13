#!/usr/bin/python

import sys
import re

def usage():
    print('Usage: `pd-gui-parser [--ptr-len 8[,16]] file [other files ... ]`')
    return -1

def detokenize(tokens):
    out = ''
    for n in range(0, len(tokens)):
        token = tokens[n]
        if type(token) is not list and type(token) is not str:
                print("ERROR, FOUND NON-LIST, NON-STRING TOKEN", token)
        if type(token) is str:
            out = out + ' ' + token
        else:
            out = out + ' {' + detokenize(token) + '}'
    return out

def tokenize(string):
    string = string + ' ' # force termination
    string = re.sub('[ \t]{1,}', ' ', string) # remove duplicated spaces to make detection more reliable
    # detect [list ... ] and turn it into {... }
    # this could be done via regexp, but the loops below should make it easier
    # to handle escaping appropriately (TODO)
    # no need to recurse this as it will be detected as a token below and will
    # be recursed then
    nest = 0
    n = 0
    while n < len(string):
        c = string[n]
        if '[' == c:
            if 0 == nest:
                bracketStart = n
            nest = nest = 1
        if ']' == c:
            nest = nest - 1
            if 0 == nest:
                substr = string[bracketStart:n+1]
                trail = string[n+1:]
                # detect [list
                regex = r'^\[\s*list\b'
                match = re.search(regex, substr)
                if match:
                    # replace leading [list
                    substr = re.sub(regex, '{', substr)
                    # and trailing ]
                    substr = re.sub(r'\]$', '}', substr)
                    string = string[0:bracketStart] + substr + trail
                    # update pointer to end of replacement
                    n = bracketStart + len(substr) -1
        n = n + 1
    nest = 0
    token = ''
    tokens = []
    maxNests = []
    whitespaces = []
    maxNest = 0
    whitespace = 0
    # recursively process { } entries
    for n in range(len(string)):
        # TODO: handle escaped characters
        c = string[n]
        tokenEnds = False
        if '{' == c:
            if 0 != nest:
                token = token + c
            nest = nest + 1
            maxNest = max(nest, maxNest)
        elif '}' == c:
            nest = nest - 1
            if 0 != nest:
                token = token + c
            if 0 == nest:
                tokenEnds = True
        elif ' ' == c and 0 == nest:
            tokenEnds = True
        else:
            token = token + c
            if ' ' == c:
                whitespace = whitespace + 1
        if tokenEnds:
            if token:
                tokens.append(token)
                maxNests.append(maxNest)
                whitespaces.append(whitespace)
                maxNest = 0
                whitespace = 0
            token = ''

    for n in range(len(tokens)):
        if maxNests[n] > 1 or (1 == maxNests[n] and whitespaces[n] >= 1):
            tokens[n] = tokenize(tokens[n])
    return tokens

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
            firstLine = True
            isPdLog = True
            for line in ifile:
                line = line.strip()
                # quick check for whether it's XML. This allows us to process
                # svg file without much effort
                # TODO: it would be safer to parse it and replace all IDs via
                # dictionary
                if "<?xml version='1.0'?>" == line:
                    isPdLog = False
                firstLine = False
                if isPdLog:
                    guiLineSignature = '^>>'
                    res = re.search(guiLineSignature, line)
                    # ignore some lines. Do so by setting them to blank so that line
                    # numbers match before and after translation
                    if not res:
                        # ignore non-GUI line
                        line = ''
                    # remove GUI signature
                    line = re.sub(guiLineSignature, '', line).strip()
                    if line == "pdtk_ping":
                        line = ''
                    if re.search('^lappend ::tmp_path {', line):
                        lappendCount = lappendCount + 1
                        if 5 == lappendCount:
                            # the fifth entry normally is the extra/ folder that is
                            # relative to the path of the executable. Ignore it
                            if re.search('^lappend ::tmp_path {.*/extra}', line):
                                line = ''
                    # "lint" tcl syntax
                    line = re.sub('[ \t]{1,}', ' ', line) # remove duplicated spaces
                    line = re.sub('\{[ \t]{1,}', '{', line) # remove spaces around braces
                    line = re.sub('[ \t]{1,}\}', '}', line) # remove spaces around braces
                    line = re.sub('[ \t]$', '', line) # remove trailing spaces
                    line = re.sub(';$', '', line) # remove trailing semicolons
                    line = re.sub('[ \t]$', '', line) # remove trailing spaces
                    # tokenize and rebuild with braces
                    """
                    # some example lines for testing {,de}tokenize
                    #line  ="{set} ::sys_staticpath {{a b c} {a b {e f g} c d } {/Users/giulio/pure-data/extra}}"
                    #line = "rr {qq} {aa bb cc} {dd ee {ff gg hh} ii mm } {nn} pp"
                    #line = "a b {e f g} c d"
                    line = "cc dd ee {one two} [ list aa bb cc ][list dd ee ff gg]{another four four2 four3} three"
                    """
                    tokens = tokenize(line)
                    line = detokenize(tokens)

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
