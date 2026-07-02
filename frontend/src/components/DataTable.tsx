import {
  CircularProgress,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  Typography,
} from "@mui/material";
import { ReactNode, useEffect, useMemo, useState } from "react";

export interface DataColumn<T> {
  key: keyof T | string;
  label: string;
  align?: "left" | "right" | "center";
  render?: (row: T) => ReactNode;
}

interface DataTableProps<T> {
  rows: T[];
  columns: DataColumn<T>[];
  getRowId: (row: T) => number | string;
  actions?: (row: T) => ReactNode;
  emptyText?: string;
  loading?: boolean;
  pagination?: boolean;
  initialPageSize?: number;
}

export function DataTable<T>({
  rows,
  columns,
  getRowId,
  actions,
  emptyText = "Nenhum registro encontrado.",
  loading = false,
  pagination = true,
  initialPageSize = 10,
}: DataTableProps<T>) {
  const colSpan = columns.length + (actions ? 1 : 0);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(initialPageSize);
  const visibleRows = useMemo(
    () => (pagination ? rows.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage) : rows),
    [page, pagination, rows, rowsPerPage],
  );

  useEffect(() => {
    setPage(0);
  }, [rows.length, rowsPerPage]);

  return (
    <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2 }}>
      <Table size="small">
        <TableHead>
          <TableRow>
            {columns.map((column) => (
              <TableCell key={String(column.key)} align={column.align}>
                {column.label}
              </TableCell>
            ))}
            {actions ? <TableCell align="right">Acoes</TableCell> : null}
          </TableRow>
        </TableHead>
        <TableBody>
          {loading ? (
            <TableRow>
              <TableCell colSpan={colSpan}>
                <Stack alignItems="center" py={3}>
                  <CircularProgress size={24} />
                </Stack>
              </TableCell>
            </TableRow>
          ) : rows.length === 0 ? (
            <TableRow>
              <TableCell colSpan={colSpan}>
                <Typography variant="body2" color="text.secondary" align="center" py={3}>
                  {emptyText}
                </Typography>
              </TableCell>
            </TableRow>
          ) : (
            visibleRows.map((row) => (
              <TableRow key={getRowId(row)} hover>
                {columns.map((column) => (
                  <TableCell key={String(column.key)} align={column.align}>
                    {column.render ? column.render(row) : String(row[column.key as keyof T] ?? "")}
                  </TableCell>
                ))}
                {actions ? <TableCell align="right">{actions(row)}</TableCell> : null}
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
      {pagination && !loading && rows.length > 0 ? (
        <TablePagination
          component="div"
          count={rows.length}
          page={page}
          rowsPerPage={rowsPerPage}
          rowsPerPageOptions={[10, 25, 50]}
          labelRowsPerPage="Linhas por pagina"
          labelDisplayedRows={({ from, to, count }) => `${from}-${to} de ${count}`}
          onPageChange={(_, nextPage) => setPage(nextPage)}
          onRowsPerPageChange={(event) => {
            setRowsPerPage(Number(event.target.value));
            setPage(0);
          }}
        />
      ) : null}
    </TableContainer>
  );
}
