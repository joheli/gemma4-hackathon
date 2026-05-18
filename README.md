# Contribution to `The Gemma 4 Good Hackathon`

## Prerequisites for running the demo

Please make sure you have a computer with the following software installed: git, docker, docker compose. Also, you need to have access to a ollama server with `Gemma 4` installed.

## Run the demo

From the command line, type `git clone https://github.com/joheli/gemma4-hackathon.git`. Then change into directory `gemma4-hackathon` and first change entry `ollama_host` in 
the config file [config.toml](data_and_config/config.toml), so it points to a ollama server that you have access to. Then, type `docker compose up -d`: this should fire up the demo and make it available at 
port 8501. If you are accessing the demo from the same computer, you should see the demo under `http://localhost:8501` using your browser.

## Backgrouund

### Purpose

This demo showcases the image classification capabilities of [Gemma 4](https://deepmind.google/models/gemma/gemma-4/), which is a family of open-weight large language models from Google Deepmind.
The current application aims at categorizing images of solid media from a routine microbiologic laboratory into `Positive` and `Negative`, depending on whether colonies are visible on the agar.

### Data

Images were acquired from a smartphone from to be discarded media at [MDI Limbach Berlin](https://www.mdi-limbach-berlin.de/) which is a private laboratory belonging to the [Limbach Gruppe](https://www.limbachgruppe.com/). Image file are anonymized values
and retain no relationship to laboratory numbers. Batches of four plates each were placed on a background containing ArUCo Markers to facilitate segmenting and cropping using package [arucutter](https://github.com/joheli/arucutter.git). 

### The demo app

The demo is served via [streamlit](https://streamlit.io/) from docker image [streamlighter](https://github.com/joheli/streamlighter.git). Gemma 4 is hosted on a local [ollama](https://ollama.com/) server and accessed via 
package [oneshot](https://github.com/joheli/oneshot.git).

## Config

The configuration can be changed in file [config.toml](data_and_config/config.toml). At the very least, you should change the entry for `ollama_host` - this should point at a ollama server under your control.

## Disclaimer

The demo was created by [Johannes Elias](https://johanneselias.net), who is a specialist in Medical Microbiology and a managing director at [MDI Limbach Berlin](https://www.mdi-limbach-berlin.de/). It is intended exclusively to foster scientific exchange. AI applications for the reading of plates are not part of routine diagnostics at [MDI Limbach Berlin](https://www.mdi-limbach-berlin.de/) and their use is currently not planned.
