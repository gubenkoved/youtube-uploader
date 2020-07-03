# Purpose

Allows to automatically backup your videos to your YouTube account.

# Features

* Fully automated upload procedure
* Automatic hash-based detection of already uploaded files (only when uploaded by the script, uses description to store metadata)
* Caching for the file hashes to avoid repeated calculation
* Ability to specify cut-off period for files to exclude files created earlier

# Prerequisites

## Install Python

Python version 3.8.0 or higher is required.

## Install pip requirements

`pip install -r requirements.txt`

## Register an application

In order to use script, you will need to register an application via Google Developer Console and put your Client ID and Client Secret in `client_secrets.json`.

Navigate to `https://console.developers.google.com/` and create a new project.

Go to `Credentials` section and create OAuth Client ID credentials, select "Desktop application" when prompted the application type.

> You will have to setup an OAuth concent screen, but you simply can put an application name into it, anything else is not required.

## Add YouTube Data API to your application

Navigate to `https://console.developers.google.com/apis/library/youtube.googleapis.com` or find the API in the Developer Console in the APIs section (search for YouTube Data API V3).

Click "Enable" button to add the API to your application.

## Put credentials to the client_secrets.json

Simply put the Client ID and Client Secret into the client_secrets.json file.

# Usage

The following command will upload all video files in the specified directory (including sub-directories) to specified playlist.

`.\youtube_uploader.py --dir "LOCAL_DIRECTORY_TO_BACKUP" --playlist "PLAYLIST_TITLE_OR_SUBSTRING"`

## Optional arguments

* `--client-secrets-file` -- path to the client secrets file, default is 'client_secrets.json'
* `--credentials-file` -- path to the credentials file, default is 'credentials.json'
* `--creation-date-cutoff` -- date in 'YYYY-MM-DD' format (e.g. `2019-01-20`) that specified a cut of by file creation date
* `--log-level` -- log level (`DEBUG`/`INFO`/`WARNING`/`ERROR`), default is `INFO`

> NOTE: Specifying paths to credentials/secret files allow to easily run the same script with multiple registered applications to bypass the quotas.

> NOTE: First time your run application or when Access Token expires you will be prompted to navigate to the link specified by application and authorize the application to access your account. Authorization page will return you the code you will need to provide back to the application to acquire credentials. These credentials will be stored in credentials.json file for future use.

# Limitations

Each Google Project gets a specific quota per day. For YouTube DataAPI it's 10'000 units, and each video upload takes slightly more than 1'600 units. It means that on a daily basis it's only possible to automatically upload **up to 6 videos per day** per Google Project. However, it might be enough as it's possible to fully automate the execution of the backup script and such capacity could be fine.

Additionally, note that quotas are applied against the Google Project, and **multiple projects** can be created.

Please also note that you can apply for **extended quotas** by filling the form (https://support.google.com/youtube/contact/yt_api_form?hl=en) -- my application for 10x quota was fulfilled, however it took more than a week.
