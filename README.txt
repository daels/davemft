Thank you for using daveMFT!

This script recovers $30 File Name attributes from slack space of
$90 Index Root attributes in an MFT.

These slack attributes are created when files are permanently 
deleted (maybe recycled too?) on an NTFS file system as the $90
shrinks but does not overwrite the slack space.

Usage:
      daveMFT.py MFTfile
      
A text file named RecoveredFNAttributes.txt will be created in the
current directory with the results found.

Please direct feedback, suggestions, and comments to davidpany@gmail.com

Thanks!
