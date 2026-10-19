# Vendored front-end libraries

These files are copied unchanged (apart from removing the trailing source-map comment)
from the official npm packages so the application works **offline**, with no CDN:

- Bootstrap 5.3.3 (MIT licence) - `bootstrap/`
- Bootstrap Icons 1.11.3 (MIT licence) - `bootstrap-icons/`

No external font service is used. The interface font stack starts with "Inter"
(used only if it is installed on your computer) and then falls back to system fonts.
