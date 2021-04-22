# C964
C964 is a re-package of part of my C964 capstone project for WGU. I'm hoping to extend this to a real project. 
C964 is intended to provide an API endpoint to extract meaningful text from photos of prescription bottle labels. 

## Installation
C964 should be installed from the provided dockerfile. <TODO>
Flask, included, will launch in self-hosted debug mode, binding to 0.0.0.0:5000
 Docker EG: docker run -d -p 5000:5000 --name c964_host c964:1.0

## Dependencies

## Usage

## TODO 
  * Clean up dependencies and packaging
  * Re-factor text parsing
  * Automate label corner detection / tagging
  * User Preference Page
  * User Creation Page
  * Password Reset
  * Pass appropriate configuration to uWGSI and NGINX, in place of defualt host
  * Launcher script to select debug or production modes
