Test that repeated executions of Pd generate consistent behaviour with respect to the GUI.

Currently supports testing messages sent to the GUI as well as svg generated from the patch.
As these messages and svgs include pointers that are instance-specific, we have to replace those with instance-agnostic identifiers, which allow meaningful comparison between distinct executions.
This translation is performed by `pd-gui-parser`.

`pd-gui-tester` runs several instances of Pd, possibly using distinct builds and compares that they all produce the same output as the reference version. The patch is supposed to quit automatically after a while.
**You are not supposed to move the mouse or press any keys while the script runs. For best results, keep the mouse out of the Pd windows.**

### Requirements

Apart from Python 3 you'll need one or more builds of Pd that you want to test.
This was tested with Python 3.9.13 on macos 10.14.6 . Not sure whether there are any modules that need installing, or version-specific tricks.

### Usage:

```
python3 pd-gui-tester [opts] [pd binaries] [pd args]
```

#### `[opts]`

`--log`: perform tests on Pd's logs

`--svg`: perform test on the generated svgs

`--count`: how many times to test the specified binaries (default: 1)

`--no-pd`: do not run the Pd binaries. Only use this with `--tmp` or it won't work.

`--tmp`: sets the folder to be used for temporary files. This will not be created or cleaned. The system tmp folder will be used otherwise and it will be cleaned in case of success.

`--ptr-len`: allows to set the expected lengths of hex sequences used for pointers. If unspecified, they will be assumed to be between 8 and 16 digits large. Range can be specified e.g.: `--ptr-len 8,16` is default

#### `[pd binaries]`:
a list of full paths to a Pd binary to test. You can specifiy the same binary several times if you want to test its self-consistency (or use `--count`)

#### `[pd args]`:
a list of arguments to be passed to Pd. This should include any patch you want to test with. Pd needs to quit automatically from the program. The first element of the list has to start with a `-` or it will be interpreted as another pd binary. The character sequence `{}` will be replaced with an instance-specific path to a tmp file. If `--svg` is used, the patch must append `.svg` to this and use it to generate an svg of the patch via the patch2svg GUI plugin.

#### Return value

0 if all tests completed successfully, an error code otherwise.

Example:

```
python3 ~/pure-data-gui-testing/pd-gui-tester --svg --log --ptr-len 12 ~/pure-data/src/pd ~/libpd/pure-data/src/pd -send "autostart 1" -send "autoquit 1" -send "svgSavePath {}.svg" ./test-gui.pd
```

