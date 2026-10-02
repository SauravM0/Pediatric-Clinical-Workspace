# IAP wall-chart replica (plain HTML + CSS)

`girls.html` and `boys.html` redraw the two wall charts in `../Images` ("WHO 2006 & IAP 2015 combined
Girls/Boys Charts 0-18 Years") using only HTML, one CSS file (`chart.css`) and inline SVG paths for the lines.
Open either file in a browser; nothing else is needed. The sheet scales with the window width.

What is on each page: title, grid paper (72 x 175 boxes girls / 72 x 195 boys: 0.25 y by 1 unit, bold every
1 y and 5 units), 7 height + 7 weight centile lines (3rd height line red), right-hand labels, axis titles,
the BMI quick-assessment inset (UW / OW / OB lines), the MPH percentile calculator (150-190 cm table with
centile marks and bar) and the footnotes.

Where the numbers come from (everything read from the two images, nothing from the app):
- `source/1_read_lines_from_image.py` - finds every line's centre in each pixel column of the image.
- `source/2_fit_curves.py` - fits a smooth curve through those readings (0.05 y steps, fit error about 0.06 cm / kg).
- `source/3_read_inset_lines.py` - same for the three inset lines.
- `source/*.json` - the resulting numbers. `build_replica.py` writes the two HTML files from them.

Check: rendered at the original size, 99% of the replica's line pixels lie within 2 px of an original line,
and 99% of the original's lines are covered by the replica.

Not copied: the typo "Heing" in the girls chart's y-axis title is written "Height".
