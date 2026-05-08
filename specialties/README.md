# Specialty Modules

- `specialties/breast/config.py`: 乳癌模組設定與顯示資訊
- `specialties/breast/review_support.py`: 前端/表單可重用的欄位定義
- `specialties/breast/toolkit.py`: IHC4、AJCC、整體分層的模組化入口
- `specialties/breast/postprocess.py`: 與 loader 介面對齊的專科後處理層
- `specialties/breast/ihc4_predictor.py`、`ajcc_converter.py`、`stratification.py`: 可單獨替換的功能 wrapper

目前先整理乳癌模組，後續若要擴其他癌別，可沿用相同結構。
