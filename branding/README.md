# pasc branding

* `logo.svg`: the logo (the `:=` of Pascal and pascdb's step marker); `logo.png` is it at 512x512.
* `social.png`: GitHub's social preview (1280x640), made from `social.html`:

```
chrome --headless --hide-scrollbars --force-device-scale-factor=1 \
	--window-size=1280,640 --screenshot=social.png file://$PWD/social.html
```
