# Purpose

Allows to automatically backup your videos to your YouTube account.

# Features

* Fully automated upload procedure
* Automatic detection of already uploaded files (only when uploaded by the script, uses descriptino to store metadata)

# Prerequsites

## Install Python

Python version 3.8.0 or higher is required.

## Install pip requirements

`pip install -r requirements.txt`

## Register an application

In order to use script, you will need to register an application via Google Developer Console and put your Client ID and Client Secret in `client_secrets.json`.

Navigate to `https://console.developers.google.com/` and create a new project.

Go to `Credentials` section and create OAuth Client ID credentials, select "Desktop application" when prompted the application type.

## Add Youtube Data API to your application

Navigate to `https://console.developers.google.com/apis/library/youtube.googleapis.com` or find the API in the Developer Console in the APIs section (search for YouTude Data API V3).

Click the button to add the API to your applciation.

## Put credentials to the client_secrets.json

Simply put the Client ID and Client Secret into the client_secrets.json file.

# Usage

The following command will upload all video files in the specified directory (including sub-directories) to specified playlist.

`.\youtube_uploader.py --dir "LOCAL_DIRECTORY_TO_BACKUP" --playlist "PLAYLIST_TITLE_OR_SUBSTRING"`



> NOTE: First time your run application or when Access Token expires you will be promted to navigate to the link specified by application and authorize the application to access your account. Authorization page will return you the code you will need to provide back to the application to aquire credentials. These credentials will be stored in credentials.json file for future use.