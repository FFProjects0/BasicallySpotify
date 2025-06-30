![Untitled25_20250502051553](https://github.com/user-attachments/assets/6fd49149-ee87-49f1-8c84-94393e65a85f)

[![Issues Badge][issues-shield]][issues-url]
[![Stars Badge][stars-shield]][stars-url]
[![Downloads Badge][downloads-shield]][downloads-url]
<!-- Issues Badge -->
[issues-shield]: https://img.shields.io/github/issues/FFProjects0/BasicallySpotify?style=flat&label=Issues&labelColor=001224&color=1DB954
[issues-url]: https://github.com/FFProjects0/BasicallySpotify/issues
<!-- Stars Badge -->
[stars-shield]: https://img.shields.io/github/stars/FFProjects0/BasicallySpotify?style=flat&label=Stars&labelColor=001224&color=1DB954
[stars-url]: https://github.com/FFProjects0/BasicallySpotify/stargazers
<!-- Downloads Badge -->
[downloads-shield]: https://img.shields.io/github/downloads/FFProjects0/BasicallySpotify/total.svg?style=flat&label=Downloads&labelColor=001224&color=1DB954
[downloads-url]: https://github.com/FFProjects0/BasicallySpotify/releases/

An easy to use music player written in Python. BasicallySpotify has support for [OnTheSpot](https://github.com/justin025/onthespot/tree/v1.1.0)'s default folder structure, lyrics and playlists! The app only includes a GUI frontend since no other versions exist. To get started [download the app here.](https://github.com/FFProjects0/BasicallySpotify/releases)<br>
<!--![image](https://github.com/user-attachments/assets/23415053-18b3-45c9-b5e5-ba6617268498)-->

> [!CAUTION]
> It appears that i've lost the python file for the newest version (v1.1.1), because i'm dumb and don't know how to properly save stuff, so the next version(s) will come out from v1.1.0.
> **The current program works good enough for everyday use, so it's not that big of a deal**

> [!WARNING]
> This program is in a very unfinished state and may contain bugs and lack features, please report and feature requests/bugs [here](https://github.com/FFProjects0/BasicallySpotify/issues).

# Quick Links
- [Features.md](https://github.com/FFProjects0/BasicallySpotify/blob/main/FEATURES_LIST.md)<br><br>
- [How to Setup](https://github.com/FFProjects0/BasicallySpotify?tab=readme-ov-file#how-to-setup)<br>
    - [OnTheSpot](https://github.com/FFProjects0/BasicallySpotify?tab=readme-ov-file#11-onthespot)<br>
    - [Manually](https://github.com/FFProjects0/BasicallySpotify?tab=readme-ov-file#121-manually)<br>
- [How to use](https://github.com/FFProjects0/BasicallySpotify?tab=readme-ov-file#how-to-use)<br>

# How to setup
## #1.1 OnTheSpot
This program is designed to work with a fork of [OnTheSpot](https://github.com/justin025/onthespot/releases/tag/v1.1.0) by justin025.
If you use this program to download songs from spotify, you don't have to do anything, just put the exe into your OnTheSpot folder and launch it.
![image](https://github.com/user-attachments/assets/974b81f1-1c17-4a24-8119-b02a5dff8469)

Upon launching, you will be greeted by a black box with a entry bar at the top, simply put the folder you use for your tracks, but **MAKE SURE IT MATCHES**.<br>
![image](https://github.com/user-attachments/assets/0484257b-62d7-4d47-bde6-413cadf6ba2e)<br>
Then it will be indexed and you can now use it!


## #1.21 Manually
[OnTheSpot](https://github.com/justin025/onthespot/releases/tag/v1.1.0) has a specific file structure that it follows:
```
Artist(s)
    ┗━━━Album(s)
          ┗━━━Songs(s).mp3/Lyrics(s).lrc
```
![image](https://github.com/user-attachments/assets/6a18dac4-e718-4f02-aefe-d153263664eb)<br>
Use this structure for the program to find your songs.

**ADD METADATA TO YOUR SONGS!**<br>
![image](https://github.com/user-attachments/assets/15b9ca95-d151-44b6-ae60-c5d74e08ebbc)<br>
I use metadata to find out information about the songs and it won't work otherwise. (it will, but the album name, artist name, song name, cover, etc. will be empty)

# How to use
Drag an album from an artist into the player area.<br>



https://github.com/user-attachments/assets/a5d69487-02fc-47b3-9a19-70c1ce55b77d



If you encounter any bugs or need additional help, please create an issue [here](https://github.com/FFProjects0/BasicallySpotify/issues) with the appropriate tags.
