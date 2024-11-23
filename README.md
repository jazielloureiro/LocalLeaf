# LocalLeaf

This tool provides an easy way to synchronize Overleaf projects from and to your local computer. No paid account necessary.

## Features
- Sync your locally modified `.tex` (and other) files to your Overleaf projects
- Sync your remotely modified `.tex` (and other) files to computer
- Works with free Overleaf account
- No Git or Dropbox required
- Does not steal or store your login credentials (works with a persisted cookie, logging in is done on the original Overleaf website)

## How To Use
### Install
The package is available via [PyPI](https://pypi.org/project/localleaf/). Just run:

```
pip3 install localleaf
```

That's it! Depending on your local Python installation, you might need to use `pip` instead of `pip3`.

### Prerequisites
- Create your project on [Overleaf](https://www.overleaf.com/project), for example a project named `test`. localleaf is not able to create projects (yet).
- Create a folder, preferably with the same name as the project (`test`) on your computer.
- Execute the script from that folder (`test`).
- If you do not specify the project name, localleaf uses the current folder's name as the project name.

### Usage
#### Login
```
lleaf [--cookie-path -v/--verbose] login
```

Logging in will be handled by a mini web browser opening on your device (using Qt5). You can then enter your username and password securely on the official Overleaf website. You might get asked to solve a CAPTCHA in the process. Your credentials are sent to Overleaf over HTTPS.

It then stores your *cookie* (**not** your login credentials) in a hidden file called `.olauth` in your system configuration directory. It is possible to store the cookie elsewhere using the `--cookie-path` option. The cookie file will not be synced to or from Overleaf.

Keep the `.olauth` file save, as it can be used to log in into your account.

### Listing all projects
```
lleaf [--cookie-path -v/--verbose] list
```

Use `lleaf list` to conveniently list all projects in your account available for syncing. 

### Downloading project's PDF
```
lleaf [--cookie-path -v/--verbose] download [-n/--name --download-path]
```

Use `lleaf download` to compile and download your project's PDF. Specify a download path if you do not want to store the PDF file in the current folder. Currently only downloads the first PDF file it finds. Using the `-n/--name` option allows you to specify a different Overleaf project name than the name of the folder you're calling `lleaf` from.

### Pulling and pushing changes
```
lleaf [--cookie-path -v/--verbose] pull [-n/--name -p/--path -i/--olignore]
```

```
lleaf [--cookie-path -v/--verbose] push [-n/--name -p/--path -i/--olignore]
```

Use `lleaf pull` to pull your Overleaf project files to your local project and `lleaf push` to push your local project files to your Overleaf project. When there are changes both locally, and remotely you will be asked which file to keep. If a file has been deleted on the source it can either be deleted on the target as well, restored on the source or ignored.

The `-n/--name` option allows you to specify a different Overleaf project name than the name of the folder you're calling `lleaf` from. The `-p/--path` option allows you to specify a different sync folder than the one you're calling `lleaf` from. The `-i/--olignore` option allows you to specify the path of an `.olignore` file. It uses `fnmatch` internally, so it may have some similarity to `.gitignore` but doesn't work exactly the same. For example, if you wish to exclude a specific folder named `out`, you need to specify it as `out/*`. See [here](https://docs.python.org/3/library/fnmatch.html) for more information.

## Known Bugs
- When modifying a file on Overleaf and immediately syncing afterwards, the tool might not detect the changes. Please allow 1-2 minutes after modifying a file on Overleaf before syncing it to your local computer.

## Contributing

All pull requests and change/feature requests are welcome.

## Disclaimer
THE AUTHOR OF THIS SOFTWARE AND THIS SOFTWARE IS NOT ENDORSED BY, DIRECTLY AFFILIATED WITH, MAINTAINED, AUTHORIZED, OR SPONSORED BY OVERLEAF OR WRITELATEX LIMITED. ALL PRODUCT AND COMPANY NAMES ARE THE REGISTERED TRADEMARKS OF THEIR ORIGINAL OWNERS. THE USE OF ANY TRADE NAME OR TRADEMARK IS FOR IDENTIFICATION AND REFERENCE PURPOSES ONLY AND DOES NOT IMPLY ANY ASSOCIATION WITH THE TRADEMARK HOLDER OF THEIR PRODUCT BRAND.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

THIS SOFTWARE WAS DESIGNED TO BE USED ONLY FOR RESEARCH PURPOSES. THIS SOFTWARE COMES WITH NO WARRANTIES OF ANY KIND WHATSOEVER. USE IT AT YOUR OWN RISK! IF THESE TERMS ARE NOT ACCEPTABLE, YOU AREN'T ALLOWED TO USE THE CODE.

