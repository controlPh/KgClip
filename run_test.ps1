$process = Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList "test_milvus_frame_path_data.py" -NoNewWindow -PassThru -Wait
$process.ExitCode
