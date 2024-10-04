from generatewds import iterate_parquet_rows

def test_iterate_parquet_rows():
    file_path = "test/parquet/sample.parquet"
    print(f"Testing file: {file_path}")
    count_rows = 0
    data_generator = iterate_parquet_rows(file_path, chunk_size=1000)
    first_batch = next(data_generator, None)

    assert first_batch is not None, "The first batch should not be None"

    assert hasattr(first_batch, 'shape'), "The batch should be a DataFrame with a 'shape' attribute"
    
    expected_columns = {'URL', 'TEXT'}
    assert expected_columns.issubset(first_batch.columns), "DataFrame should contain specific columns"

    for batch in data_generator:
        count_rows += len(batch)

    assert count_rows > 0, "The number of rows should be greater than 0"

    n = 9719
    assert count_rows == n, f"The number of rows should be equal to {n}"


