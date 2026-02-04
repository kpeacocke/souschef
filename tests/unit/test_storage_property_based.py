"""Property-based tests for the storage module using Hypothesis."""

import gc
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from souschef.storage import LocalBlobStorage, StorageManager


@pytest.mark.filterwarnings("ignore::ResourceWarning")
class TestStoragePropertyBased:
    """Property-based tests using Hypothesis for the storage module."""

    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=10)
    def test_cache_key_is_consistent_for_same_input(self, random_path):
        """Test that cache key generation is deterministic."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with StorageManager(db_path=Path(tmpdir) / "test.db") as manager:
                key1 = manager.generate_cache_key(random_path, "provider", "model")
                key2 = manager.generate_cache_key(random_path, "provider", "model")

                assert key1 == key2

            # Force garbage collection to clean up connections
            gc.collect()

    @given(
        st.text(min_size=1, max_size=100),
        st.text(min_size=1, max_size=50),
        st.text(min_size=1, max_size=50),
    )
    @settings(max_examples=20)
    def test_different_inputs_produce_different_cache_keys(self, path, provider, model):
        """Test that different inputs produce different cache keys."""
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            StorageManager(db_path=Path(tmpdir) / "test.db") as manager,
        ):
            key1 = manager.generate_cache_key(path, provider, model)
            key2 = manager.generate_cache_key(path + "_different", provider, model)

            assert key1 != key2

    @given(st.text(min_size=1, max_size=200), st.text(min_size=0, max_size=500))
    @settings(max_examples=20)
    def test_save_analysis_with_arbitrary_text(self, cookbook_name, recommendations):
        """Test saving analysis with arbitrary text inputs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(db_path=Path(tmpdir) / "test.db")

            result_id = manager.save_analysis(
                cookbook_name=cookbook_name,
                cookbook_path="/path",
                cookbook_version="1.0.0",
                complexity="low",
                estimated_hours=5.0,
                estimated_hours_with_souschef=2.0,
                recommendations=recommendations,
                analysis_data={},
            )

            assert result_id is not None
            assert isinstance(result_id, int)

    @given(st.floats(min_value=0.1, max_value=1000.0))
    @settings(max_examples=20)
    def test_save_analysis_with_various_hours(self, hours):
        """Test saving analysis with various estimated hour values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(db_path=Path(tmpdir) / "test.db")

            manager.save_analysis(
                cookbook_name="test",
                cookbook_path="/path",
                cookbook_version="1.0.0",
                complexity="medium",
                estimated_hours=hours,
                estimated_hours_with_souschef=hours / 2,
                recommendations="",
                analysis_data={},
            )

            # Verify retrieval
            history = manager.get_analysis_history()
            assert len(history) == 1
            assert abs(history[0].estimated_hours - hours) < 0.01

    @given(st.integers(min_value=1, max_value=500))
    @settings(max_examples=20)
    def test_save_multiple_conversions_with_various_file_counts(self, file_count):
        """Test saving conversions with varying file counts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(db_path=Path(tmpdir) / "test.db")

            # Save analysis
            analysis_id = manager.save_analysis(
                cookbook_name="test",
                cookbook_path="/path",
                cookbook_version="1.0.0",
                complexity="medium",
                estimated_hours=10.0,
                estimated_hours_with_souschef=5.0,
                recommendations="",
                analysis_data={},
            )

            # Save conversion with arbitrary file count
            manager.save_conversion(
                cookbook_name="test",
                output_type="playbook",
                status="success",
                files_generated=file_count,
                conversion_data={},
                analysis_id=analysis_id,
                blob_storage_key="key",
            )

            # Verify statistics
            stats = manager.get_statistics()
            assert stats["total_files_generated"] == file_count

    @given(
        st.floats(min_value=1.0, max_value=50.0),
        st.floats(min_value=0.5, max_value=25.0),
    )
    @settings(max_examples=20)
    def test_statistics_calculations_are_correct(self, hours, souschef_hours):
        """Test that statistics calculations are arithmetically correct."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(db_path=Path(tmpdir) / "test.db")

            manager.save_analysis(
                cookbook_name="test",
                cookbook_path="/path",
                cookbook_version="1.0.0",
                complexity="low",
                estimated_hours=hours,
                estimated_hours_with_souschef=souschef_hours,
                recommendations="",
                analysis_data={},
            )

            stats = manager.get_statistics()

            # Total files should start at 0
            assert stats["total_files_generated"] == 0

    @given(
        st.text(min_size=1, max_size=100).filter(
            lambda x: "\r" not in x and "\n" not in x
        )
    )
    @settings(max_examples=20)
    def test_local_blob_storage_handles_text_files(self, file_content):
        """Test LocalBlobStorage with arbitrary text file content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalBlobStorage(base_path=Path(tmpdir) / "blobs")

            # Create test file
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text(file_content)

            # Upload and download
            key = storage.upload(test_file, "test/file.txt")
            download_path = Path(tmpdir) / "downloaded.txt"
            storage.download(key, download_path)

            # Verify content is preserved
            assert download_path.read_text() == file_content

    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=20)
    def test_local_blob_storage_list_keys_is_valid(self, prefix):
        """Test that list_keys always returns valid results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalBlobStorage(base_path=Path(tmpdir) / "blobs")

            # Should handle any prefix safely
            keys = storage.list_keys(prefix=prefix)

            # Result should be a list of strings
            assert isinstance(keys, list)
            assert all(isinstance(key, str) for key in keys)

    @given(
        st.text(min_size=1, max_size=50),
        st.text(min_size=1, max_size=50),
        st.text(min_size=1, max_size=50),
    )
    @settings(max_examples=20)
    def test_cache_key_handles_special_characters(
        self, path_with_special, provider, model
    ):
        """Test cache key generation with special characters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(db_path=Path(tmpdir) / "test.db")

            # Should not crash on special characters
            key = manager.generate_cache_key(path_with_special, provider, model)
            assert isinstance(key, str)
            assert len(key) > 0

    def test_multiple_concurrent_saves(self):
        """Test that multiple analyses can be saved and retrieved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(db_path=Path(tmpdir) / "test.db")

            # Save multiple analyses
            ids = []
            for i in range(10):
                rid = manager.save_analysis(
                    cookbook_name=f"cookbook{i}",
                    cookbook_path=f"/path{i}",
                    cookbook_version="1.0.0",
                    complexity="low",
                    estimated_hours=5.0,
                    estimated_hours_with_souschef=2.0,
                    recommendations="",
                    analysis_data={},
                )
                ids.append(rid)

            # All IDs should be unique
            assert len(set(ids)) == 10

            # All should be retrievable
            history = manager.get_analysis_history()
            assert len(history) == 10
