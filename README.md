# BasicallySpotify
Custom program that works closely to spotify but for local files; no ads and with lyric support!<br>
![image](https://github.com/user-attachments/assets/23415053-18b3-45c9-b5e5-ba6617268498)


# Features
- Lyric (.lrc) support for files with timing as well without timing (examples below)<br>
Song + lyric combo<br>
![image](https://github.com/user-attachments/assets/0ab912e4-4d88-4901-acbd-707286d61a45)<br>
Timed:<br>
![image](https://github.com/user-attachments/assets/629216e5-94ff-42e4-92fa-234c91b0eaaf)<br>
Not Timed:<br>
![image](https://github.com/user-attachments/assets/2d85b973-72db-4f79-9491-560b5e63807c)<br>
- Repeat support (modes: no repeat, album repeat, one song repeat)
- Actually playing songs, whoa!
- Peak searching (search for album names or artist names)
- Playlists, though really shitty, close it rather than use it.
- and more!


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



If you encounter any bugs, please create an issue [here](https://github.com/FFProjects0/BasicallySpotify/issues).
