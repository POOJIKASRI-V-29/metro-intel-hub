"""
Table Extraction and Spatial Reconstruction module for the KMRL Platform.

This module provides heuristic spatial algorithms to cluster raw OCR tokens 
into structured tabular matrices based on bounding box coordinates.
"""

import logging
from typing import Any, Dict, List
from pydantic import BaseModel, Field

# Import the OCR structural contract from the companion module
from .paddle_ocr import OCRResultItem

# Setup logger matching Stage 0 configurations
logger = logging.getLogger("document_intelligence.ocr.table_extractor")


class TableCell(BaseModel) :
    """
    Represents a single reconstructed cell within a tabular matrix grid.
    """
    row_index: int = Field(..., description="0-based row identifier.")
    col_index: int = Field(..., description="0-based column identifier.")
    text: str = Field(..., description="Merged textual string content of the cell.")


class ReconstructedTable(BaseModel):
    """
    Data model representing a completely reconstructed table matrix structure.
    """
    total_rows: int = Field(..., description="Total count of discovered rows.")
    total_columns: int = Field(..., description="Total count of discovered columns.")
    cells: List[TableCell] = Field(..., description="Flat collection of calculated cell allocations.")
    
    def to_markdown(self) -> str:
        """
        Compiles the internal cell grid coordinates into a clean Markdown table string.
        """
        if not self.cells:
            return ""

        # Initialize an empty grid structure
        grid: List[List[str]] = [["" for _ in range(self.total_columns)] for _ in range(self.total_rows)]
        for cell in self.cells:
            grid[cell.row_index][cell.col_index] = cell.text

        markdown_lines = []
        for r_idx, row in enumerate(grid):
            markdown_lines.append(f"| { ' | '.join(row) } |")
            # Inject structural headers separator directly underneath row index 0
            if r_idx == 0:
                separator = "| " + " | ".join(["---"] * self.total_columns) + " |"
                markdown_lines.append(separator)
                
        return "\n".join(markdown_lines)


class TableExtractor:
    """
    Performs deterministic spatial clustering on OCR tokens to extract structured layouts.
    """

    def __init__(self, y_overlap_threshold: float = 0.5, x_tolerance_pixels: float = 20.0) -> None:
        """
        Initializes the spatial geometry extractor.

        Args:
            y_overlap_threshold: Percentage of vertical height overlap required to group 
                                 tokens into the same visual text row.
            x_tolerance_pixels: Pixel distance buffer to isolate distinct column boundaries.
        """
        self.y_overlap_threshold = y_overlap_threshold
        self.x_tolerance_pixels = x_tolerance_pixels

    def extract_table_from_tokens(self, ocr_items: List[OCRResultItem]) -> ReconstructedTable:
        """
        Analyzes 2D bounding boxes to cluster individual text segments into rows and columns.

        Args:
            ocr_items: List of text tokens extracted by an OCR engine.

        Returns:
            A populated ReconstructedTable container model.
        """
        if not ocr_items:
            logger.warning("Table extraction requested with empty OCR token inputs.")
            return ReconstructedTable(total_rows=0, total_columns=0, cells=[])

        # Sort items primarily top-to-bottom (Y axis), then secondarily left-to-right (X axis)
        # Bounding box structure: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        sorted_items = sorted(ocr_items, key=lambda item: (item.bounding_box[0][1], item.bounding_box[0][0]))

        # 1. Cluster Items into Rows based on vertical intersection
        rows: List[List[OCRResultItem]] = []
        for item in sorted_items:
            assigned = False
            item_y1 = item.bounding_box[0][1]
            item_y2 = item.bounding_box[2][1]
            item_height = max(1.0, item_y2 - item_y1)

            for row in rows:
                # Compare against the first element's vertical footprint in that row group
                ref_y1 = row[0].bounding_box[0][1]
                ref_y2 = row[0].bounding_box[2][1]
                ref_height = max(1.0, ref_y2 - ref_y1)

                # Calculate vertical overlap span
                overlap = min(item_y2, ref_y2) - max(item_y1, ref_y1)
                
                # Check if overlap exceeds thresholds relative to the shortest item height
                min_h = min(item_height, ref_height)
                if overlap / min_h > self.y_overlap_threshold:
                    row.append(item)
                    assigned = True
                    break

            if not assigned:
                rows.append([item])

        # Ensure tokens within each isolated row group are sorted strictly left-to-right
        for row in rows:
            row.sort(key=lambda item: item.bounding_box[0][0])

        # 2. Determine unique Column boundaries across the document workspace
        # We sample the left-most coordinate values of all tokens to build dynamic column coordinates
        all_left_coordinates = sorted([item.bounding_box[0][0] for item in ocr_items])
        column_bounds: List[float] = []
        
        for x_coord in all_left_coordinates:
            if not column_bounds:
                column_bounds.append(x_coord)
            else:
                # If coordinate is sufficiently far from the last recorded boundary, form a new column anchor
                if x_coord - column_bounds[-1] > self.x_tolerance_pixels:
                    column_bounds.append(x_coord)

        total_rows = len(rows)
        total_cols = max(1, len(column_bounds))
        reconstructed_cells: List[TableCell] = []

        # 3. Map tokens to their corresponding closest Grid intersections
        for r_idx, row_items in enumerate(rows):
            for item in row_items:
                item_x = item.bounding_box[0][0]
                
                # Identify column index by matching against the closest lower-bound anchor point
                col_idx = 0
                min_delta = float("inf")
                for c_idx, b_x in enumerate(column_bounds):
                    delta = abs(item_x - b_x)
                    if delta < min_delta:
                        min_delta = delta
                        col_idx = c_idx

                # Append or merge text if an allocation mapping already exists for that grid target
                existing_cell = next(
                    (c for c in reconstructed_cells if c.row_index == r_idx and c.col_index == col_idx), 
                    None
                )
                if existing_cell:
                    existing_cell.text += f" {item.text}"
                else:
                    reconstructed_cells.append(
                        TableCell(
                            row_index=r_idx,
                            col_index=col_idx,
                            text=item.text
                        )
                    )

        logger.info(f"Reconstructed table matrix matching {total_rows}x{total_cols} parameters successfully.")
        return ReconstructedTable(
            total_rows=total_rows,
            total_columns=total_cols,
            cells=reconstructed_cells
        )