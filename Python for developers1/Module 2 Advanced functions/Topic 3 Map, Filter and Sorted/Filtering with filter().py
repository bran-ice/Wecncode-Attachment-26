readings = [12.3, -999, 14.1, 13.0, -999, 15.2]
valid = list(filter(lambda x: x != -999, readings))
print("all readings:", readings)
print("valid readings:", valid)
readings = [12.3, -999, 14.1, 13.0, -999, 15.2]
above_13 = list(filter(lambda x: x > 13, readings))
print("all readings:", readings)
print("above 13:", above_13)
files = [
    "data_january.csv",
    "readme.txt",
    "sales.csv",
    "image.png",
    "backup.zip",
    "report.CSV",
    "archive.tar.gz",
    "notes.md",
    "DATA_2021.csv",
    "script.py"
]

csv_files = list(filter(lambda f: f.endswith('.csv'), files))
print("all files:", files)
print("csv files:", csv_files)