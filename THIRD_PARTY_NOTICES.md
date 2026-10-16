# Third-party notices

This repository's own code is MIT-licensed (see `LICENSE`). The notices below cover third-party material that the PREDICT calculator reproduces or was checked against.

## PREDICT Breast v3 coefficients (WintonCentre/predictv30r)

The PREDICT v3 coefficients and baseline-hazard constants in `assets/js/legacy-app.js` (`PREDICT_V3_COEFFS`) are taken from
`inst/extdata/coefficients_v3.csv` of https://github.com/WintonCentre/predictv30r (the PREDICT authors' public R package; its `DESCRIPTION` states `License: MIT + file LICENSE`).
The remaining v3 constants and structure (HER2 time-varying terms, Ki-67, PR, smoking and radiotherapy adjustments, treatment log hazard ratios) follow that package's `R/benefits31.R`.
The model itself is published in: Grootes I, Wishart GC, Pharoah PDP. npj Breast Cancer 2024;10:6, doi:10.1038/s41523-024-00612-y.

The license text of that package, copied verbatim from its `LICENSE.md`:

````text
# MIT License

Copyright (c) 2022 University of Cambridge

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
````

(The package's short `LICENSE` file contains only `YEAR: 2022` and `COPYRIGHT HOLDER: University of Cambridge`.)

## PREDICT v2.1 validation reference values (nhs.predict, CRAN)

`tests/predict_snapshot.json` holds reference outputs computed by running the CRAN package `nhs.predict` (current CRAN release 1.4.0, author/maintainer Giovanni Tramonti; https://cran.r-project.org/package=nhs.predict).
Only numerical outputs are stored; no source code from the package is included in this repository. The PREDICT v2.1 constants in `assets/js/legacy-app.js` (`_predictPI_ERpos` and related functions) carry a comment stating they were verified against that package's R source (`predict.os.R`); they are published model coefficients re-implemented in JavaScript, not copied code.
The package's `DESCRIPTION` declares `License: GPL-2` (the GNU General Public License, version 2: https://www.gnu.org/licenses/old-licenses/gpl-2.0.html); the CRAN repository mirror contains no separate license file, so that standard text applies. The package states that it is not affiliated with the development of NHS Predict.
