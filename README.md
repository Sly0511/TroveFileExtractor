# Trove File Extractor

This tool's purpose isn't to make yet again a poor implementation of trove's extraction methods.
<br>In this tool I decoded the TFI (Trove File Index) that allows me to directly read the contents of files directly from TFA (Trove File Archive)

This has allowed me to greatly increase the speed at which the extraction goes, capable of reducing actual extraction time down to seconds
<br>However this isn't some miracle tool, the way I achieved this performance also means there's a new step which assesses the changes that happened from update to update
<br>The tool will read every single archive and get the content of each file and compare to the already extracted files.


## How to install and run
Install required dependency from microsoft [Microsoft Visual C++ Redistributable 2015-2022](https://aka.ms/vs/17/release/vc_redist.x64.exe)
<br>Get the latest release from [Releases](https://github.com/Sly0511/TroveFileExtractor/releases)
<br>Run the `.msi` package and install the program
<br>Go to your desktop and run the program from the newly created shortcut

## Numbers
- A full extraction by my tool can be 4 times or more faster than current methods available.
- A selected extraction can be done in mere seconds allowing you to fine extract single directories if you wish.
- A changes extraction may take a little bit more but it sure is worth it
    - With the changes extraction the app will read and compare all files before extraction
    - Show a little metrics of how many changes are there to extract and only extract said changes
    - This reduces greatly the amount of writes needed to disk which is both beneficial to SSD's longevity or HDD fragmentation (avoiding it)
    - It also displays those changes in a separate folder when used in advanced mode which helps avid testers compare files and data mine the game
    - With the use of hashes this slow process of comparing can be skipped when in Performance mode (some warnings in app, pay close attention) which lets it skip mass checking files in your computer and reduce exponentially the amount of time it needs to fetch changes

## Special thanks to
- Dan (Pantong) for helping me go through the algorythmic and programming challenges.
- Etaew for motivating me back into TFA and TFI extraction after a year
- cr0nicl3 for the help building a better interface that gives a better user experience and giving me amazing feedback
- Asled for testing this tool in it's BETA tests and providing crucial feedback to improve the mechanics of using the UI
- Nik for being a nuisance and picky with his feedback and making me do 4x the work needed
- Geoflay for testing the features and making sure they worked as intended