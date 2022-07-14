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
    return out.strip()

def tokenize(string):
    string = string + ' ' # force termination
    string = re.sub('[ \t]{1,}', ' ', string) # remove duplicated spaces to make detection more reliable
    # detect [list ... ] and turn it into {... }
    # no need to recurse this as it will be detected as a token below and will
    # be recursed then
    nest = 0
    n = 0
    escapeOn = False
    cmds = []
    while n < len(string):
        c = string[n]
        if '[' == c and not escapeOn:
            if 0 == nest:
                bracketStart = n
            nest = nest = 1
        if ']' == c and not escapeOn:
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
                else:
                    cmds.append({ 'start': bracketStart, 'stop': n})
        if '\\' == c and not escapeOn:
            escapeOn = True
        else:
            escapeOn = False
        n = n + 1
    nest = 0
    token = ''
    tokens = []
    maxNests = []
    # know whether Further Processing is needed
    FP_DONT_RECURSE = 0
    FP_RECURSE = 1
    FP_RECURSE_CMD = -1
    recurse = []
    maxNest = 0
    whitespace = 0
    # recursively process { } entries
    escapeOn = False
    cmdN = 0
    if cmdN < len(cmds):
        cmdStart = cmds[cmdN]['start']
        cmdStop = cmds[cmdN]['stop']
    else:
        cmdStart = -1
        cmdStop = -1

    for n in range(len(string)):
        c = string[n]
        tokenEnds = False
        tokenIsCmd = False
        if n >= cmdStart and n <= cmdStop:
            if cmdStop == n:
                tokenEnds = True
                tokenIsCmd = True
                token = string[cmdStart : cmdStop+1]
                cmdN = cmdN + 1
                nextCmd = True
                if cmdN < len(cmds):
                    cmdStart = cmds[cmdN]['start']
                    cmdStop = cmds[cmdN]['stop']
                else:
                    cmdStart = -1
                    cmdStop = -1
        elif '{' == c and not escapeOn:
            if 0 != nest:
                token = token + c
            nest = nest + 1
            maxNest = max(nest, maxNest)
        elif '}' == c and not escapeOn:
            nest = nest - 1
            if 0 != nest:
                token = token + c
            if 0 == nest:
                tokenEnds = True
        elif ' ' == c and 0 == nest:
            tokenEnds = True
        else:
            token = token + c
            if '\\' == c and not escapeOn:
                escapeOn = True
            else:
                escapeOn = False
            if ' ' == c:
                whitespace = whitespace + 1
        if tokenEnds:
            if token:
                tokens.append(token)
                maxNests.append(maxNest)
                fp = FP_DONT_RECURSE
                if tokenIsCmd:
                    fp = FP_RECURSE_CMD
                elif whitespace:
                    fp = FP_RECURSE
                recurse.append(fp)
                maxNest = 0
                whitespace = 0
            token = ''

    for n in range(len(tokens)):
        if FP_RECURSE_CMD == recurse[n]:
            if tokens[n][0] != '[' or tokens[n][-1] != ']':
                raise('Error with token', n, 'expected to be cmd but actually got', tokens)
            tokens[n] = ['['] + tokenize(tokens[n][1:-1]) + [']']
        elif maxNests[n] > 1 or (1 == maxNests[n] and FP_RECURSE == recurse[n]):
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
            firstLine = True
            isPdLog = True
            sets = {}
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
                    # ignore some lines.
                    if not res:
                        # ignore non-GUI line
                        continue
                    # remove GUI signature
                    line = re.sub(guiLineSignature, '', line).strip()
                    # ignore pings as they happen at non-deterministic times
                    if line == "pdtk_ping":
                        continue
                    # ignore lines exporting svgs as they will have different paths
                    # these will look differently before and after
                    # da000ee4b colourful debugging output
                    #, hence why we do not run this on the tokenized string and we use the `.*`
                    if re.search('pdtk_plugin_dispatch.*::patch2svg::exportall', line):
                        continue
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
                    # Here we account for the fact that some messages have been
                    # refactored into a single one, such as
                    # from:
                    #   set ::tmp_path
                    #   lappend ::tmp_path /Users/giulio/Documents/Pd/externals
                    #   lappend ::tmp_path /Users/giulio/Documents/Pd/externals/context
                    #   lappend ::tmp_path /Users/giulio/Documents/Pd/patch2svg-plugin
                    #   set ::sys_searchpath $::tmp_path
                    # to:
                    #   set ::sys_searchpath { /Users/giulio/Documents/Pd/externals /Users/giulio/Documents/Pd/externals/context /Users/giulio/Documents/Pd/patch2svg-plugin}
                    # in:
                    #   b175797e use helper-functions for repetitive calls to pdgui_vmess()
                    # it seems that only instances using tmp_path have been
                    # replaced in that commit
                    # We discard intermediate lines and only keep the last one
                    tmpVar = '::tmp_path'
                    if len(tokens) >= 2 and 'set' == tokens[0]:
                        if 2 == len(tokens) and tmpVar == tokens[1]:
                            # initialisation
                            sets[tmpVar] = []
                            continue
                        elif 3 == len(tokens) and '$'+tmpVar == tokens[2]:
                            # assignment
                            dest = tokens[1]
                            sets[dest] = sets[tmpVar]
                            # the current line becomes the result
                            tokens = ['set', dest]
                            if len(sets[dest]):
                                tokens.append(sets[dest])
                            del sets[tmpVar]
                    if len(tokens) >= 2 and 'lappend' == tokens[0]:
                        # append
                        if tmpVar == tokens[1]:
                            for n in range(2, len(tokens)):
                                sets[tmpVar].append(tokens[n])
                            continue

                    # the path ending with 'extra' is instance-specific
                    # so we replace it
                    if 3 == len(tokens) and 'set' == tokens[0] and '::sys_staticpath' == tokens[1]:
                        for n in range(len(tokens[2])):
                            tokens[2][n] = re.sub(r'.*(\/extra[/]*)$', r'______\1', tokens[2][n])

                    line = detokenize(tokens)

                # TODO: we should do some heuristics on ptr len to ensure we
                # use consistent ptr lengths across lines and avoid false positives
                ptrRegex = '[0-9a-f]{%d,%d}' % (ptrLen[0], ptrLen[1])
                # attempt different regexes, the order is important, as we keep
                # going regardless of whether any match is found
                # NOTE: these are runnning on post-retokenized strings, so they
                # may not match verbatim what's in the input file
                regexes = [
                    # this one is a workaround to address the inconsistency of
                    # the subplot tag since tag0 was introduced in
                    # 1834a3566a411ee24b4f8e2c9f399f024c11e93a s_template:
                    # convert to pdgui_vmess()
                    '%s plot%s_array%s_onset-[0-9]+-[0-9]+\+[0-9]+' % (ptrRegex, ptrRegex, ptrRegex), # TODO: this should be only if "isPdLog"
                    # simple ptr
                    ptrRegex,
                ]
                for regex in regexes:
                    res = re.findall(regex, line)
                    for el in res:
                        if el not in dic:
                            dic[el] = '_%05d_' % dicId
                            dicId = dicId + 1
                        # translate the string
                        line = line.replace(el, dic[el])
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
