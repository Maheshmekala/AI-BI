from data_sources.base import DataSource, DataSourceRegistry, Dataset
from data_sources.file_sources import CSVSource, ExcelSource, PDFSource
from data_sources.sql_sources import PostgreSQLSource, MySQLSource, SQLiteSource, GenericSQLSource

ALL_SOURCES: dict[str, type[DataSource]] = {
    "csv": CSVSource,
    "excel": ExcelSource,
    "pdf": PDFSource,
    "postgresql": PostgreSQLSource,
    "mysql": MySQLSource,
    "sqlite": SQLiteSource,
    "generic_sql": GenericSQLSource,
}

__all__ = [
    "DataSource", "DataSourceRegistry", "Dataset",
    "CSVSource", "ExcelSource", "PDFSource",
    "PostgreSQLSource", "MySQLSource", "SQLiteSource", "GenericSQLSource",
    "ALL_SOURCES",
]
