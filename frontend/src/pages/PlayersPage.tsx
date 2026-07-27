import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
  type SortingState,
  type VisibilityState
} from "@tanstack/react-table";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, type PlayerFilters } from "../api/client";
import { ReliabilityBadge } from "../components/ReliabilityBadge";
import { StatePanel } from "../components/StatePanel";
import type { PlayerListItem, PlayerPage, Role } from "../models/api";

const columnHelper = createColumnHelper<PlayerListItem>();
const SORT_MAP: Record<string, string> = {
  display_name: "name",
  latest_season: "latest_season",
  latest_rated_appearances: "appearances"
};

function downloadCsv(items: PlayerListItem[]) {
  const headers = [
    "Nome",
    "Ruolo",
    "Squadra",
    "Stagione",
    "Pv",
    "Stagioni disponibili",
    "Affidabilità"
  ];
  const rows = items.map((item) => [
    item.display_name,
    item.latest_role ?? "",
    item.latest_team ?? "",
    item.latest_season ?? "",
    item.latest_rated_appearances ?? "",
    item.available_seasons,
    item.reliability_score.toFixed(2)
  ]);
  const escape = (value: unknown) => `"${String(value).replaceAll('"', '""')}"`;
  const content = [headers, ...rows]
    .map((row) => row.map(escape).join(";"))
    .join("\n");
  const blob = new Blob([`\uFEFF${content}`], {
    type: "text/csv;charset=utf-8"
  });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "giocatori-fantacalcio.csv";
  link.click();
  URL.revokeObjectURL(link.href);
}

export function PlayersPage() {
  const [filters, setFilters] = useState<PlayerFilters>({
    page: 1,
    pageSize: 25,
    sortBy: "name",
    sortOrder: "asc"
  });
  const [draftSearch, setDraftSearch] = useState("");
  const [draftTeam, setDraftTeam] = useState("");
  const [data, setData] = useState<PlayerPage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sorting, setSorting] = useState<SortingState>([
    { id: "display_name", desc: false }
  ]);
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});

  useEffect(() => {
    let active = true;
    setError(null);
    api
      .players(filters)
      .then((response) => active && setData(response))
      .catch((reason: unknown) => {
        if (active) {
          setError(reason instanceof Error ? reason.message : "Errore API");
        }
      });
    return () => {
      active = false;
    };
  }, [filters]);

  const columns = useMemo(
    () => [
      columnHelper.accessor("display_name", {
        header: "Giocatore",
        cell: ({ row, getValue }) => (
          <Link className="player-link" to={`/players/${row.original.id}`}>
            <span className={`role-chip role-chip--${row.original.latest_role}`}>
              {row.original.latest_role ?? "?"}
            </span>
            <strong>{getValue()}</strong>
          </Link>
        )
      }),
      columnHelper.accessor("latest_team", {
        header: "Squadra",
        enableSorting: false,
        cell: (info) => info.getValue() ?? "—"
      }),
      columnHelper.accessor("latest_season", {
        header: "Ultima stagione",
        cell: (info) => info.getValue() ?? "—"
      }),
      columnHelper.accessor("latest_rated_appearances", {
        header: "Pv",
        cell: (info) => info.getValue() ?? "—"
      }),
      columnHelper.accessor("available_seasons", {
        header: "Storico",
        enableSorting: false,
        cell: (info) => `${info.getValue()}/4`
      }),
      columnHelper.accessor("reliability_score", {
        header: "Affidabilità",
        enableSorting: false,
        cell: ({ row }) => (
          <ReliabilityBadge
            band={row.original.reliability_band}
            score={row.original.reliability_score}
          />
        )
      })
    ],
    []
  );
  const table = useReactTable({
    data: data?.items ?? [],
    columns,
    state: { sorting, columnVisibility },
    manualSorting: true,
    onColumnVisibilityChange: setColumnVisibility,
    onSortingChange: (updater) => {
      const next = typeof updater === "function" ? updater(sorting) : updater;
      setSorting(next);
      const first = next[0];
      setFilters((current) => ({
        ...current,
        page: 1,
        sortBy: first ? (SORT_MAP[first.id] ?? "name") : "name",
        sortOrder: first?.desc ? "desc" : "asc"
      }));
    },
    getCoreRowModel: getCoreRowModel()
  });

  const updateFilter = (patch: Partial<PlayerFilters>) =>
    setFilters((current) => ({ ...current, ...patch, page: 1 }));

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <span className="eyebrow">Database storico</span>
          <h1>Giocatori</h1>
          <p>Cerca, filtra e apri lo storico stagione per stagione.</p>
        </div>
        <button
          className="button button--secondary"
          type="button"
          disabled={!data?.items.length}
          onClick={() => data && downloadCsv(data.items)}
        >
          Esporta pagina CSV
        </button>
      </header>

      <form
        className="filters"
        onSubmit={(event) => {
          event.preventDefault();
          updateFilter({
            search: draftSearch.trim() || undefined,
            team: draftTeam.trim() || undefined
          });
        }}
      >
        <label className="field field--search">
          <span>Cerca per nome</span>
          <input
            value={draftSearch}
            onChange={(event) => setDraftSearch(event.target.value)}
            placeholder="Es. Dimarco"
          />
        </label>
        <label className="field">
          <span>Squadra</span>
          <input
            value={draftTeam}
            onChange={(event) => setDraftTeam(event.target.value)}
            placeholder="Es. Inter"
          />
        </label>
        <label className="field">
          <span>Ruolo</span>
          <select
            value={filters.role ?? ""}
            onChange={(event) =>
              updateFilter({ role: event.target.value as Role | "" })
            }
          >
            <option value="">Tutti</option>
            <option value="P">Portieri</option>
            <option value="D">Difensori</option>
            <option value="C">Centrocampisti</option>
            <option value="A">Attaccanti</option>
          </select>
        </label>
        <label className="field">
          <span>Presenze minime</span>
          <input
            type="number"
            min="0"
            max="38"
            value={filters.minAppearances ?? ""}
            onChange={(event) =>
              updateFilter({
                minAppearances: event.target.value
                  ? Number(event.target.value)
                  : undefined
              })
            }
          />
        </label>
        <label className="field">
          <span>Stagioni minime</span>
          <select
            value={filters.minSeasons ?? ""}
            onChange={(event) =>
              updateFilter({
                minSeasons: event.target.value
                  ? Number(event.target.value)
                  : undefined
              })
            }
          >
            <option value="">Tutte</option>
            {[1, 2, 3, 4].map((value) => (
              <option value={value} key={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
        <button className="button button--primary" type="submit">
          Applica
        </button>
        <button
          className="button button--ghost"
          type="button"
          onClick={() => {
            setDraftSearch("");
            setDraftTeam("");
            setFilters({
              page: 1,
              pageSize: 25,
              sortBy: "name",
              sortOrder: "asc"
            });
          }}
        >
          Azzera
        </button>
      </form>

      <details className="column-picker">
        <summary>Seleziona colonne</summary>
        <div className="column-picker__options">
          {table.getAllLeafColumns().map((column) => (
            <label key={column.id}>
              <input
                type="checkbox"
                checked={column.getIsVisible()}
                onChange={column.getToggleVisibilityHandler()}
              />
              {typeof column.columnDef.header === "string"
                ? column.columnDef.header
                : column.id}
            </label>
          ))}
        </div>
      </details>

      {error ? (
        <StatePanel title="Errore di caricamento" message={error} tone="error" />
      ) : !data ? (
        <StatePanel title="Caricamento" message="Ricerca giocatori in corso…" />
      ) : data.items.length === 0 ? (
        <StatePanel
          title="Nessun giocatore trovato"
          message="Prova a rimuovere uno o più filtri oppure cerca un altro nome."
        />
      ) : (
        <section className="table-panel">
          <div className="table-summary">
            <strong>{data.total_items.toLocaleString("it-IT")} risultati</strong>
            <span>
              Pagina {data.page} di {data.total_pages || 1}
            </span>
          </div>
          <div className="table-scroll">
            <table>
              <thead>
                {table.getHeaderGroups().map((headerGroup) => (
                  <tr key={headerGroup.id}>
                    {headerGroup.headers.map((header) => (
                      <th key={header.id}>
                        {header.isPlaceholder ? null : (
                          <button
                            className="table-sort"
                            type="button"
                            disabled={!header.column.getCanSort()}
                            onClick={header.column.getToggleSortingHandler()}
                          >
                            {flexRender(
                              header.column.columnDef.header,
                              header.getContext()
                            )}
                            {{
                              asc: " ↑",
                              desc: " ↓"
                            }[header.column.getIsSorted() as string] ?? ""}
                          </button>
                        )}
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
              <tbody>
                {table.getRowModel().rows.map((row) => (
                  <tr key={row.id}>
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id}>
                        {flexRender(
                          cell.column.columnDef.cell,
                          cell.getContext()
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="pagination">
            <button
              className="button button--ghost"
              type="button"
              disabled={data.page <= 1}
              onClick={() =>
                setFilters((current) => ({
                  ...current,
                  page: Math.max(1, (current.page ?? 1) - 1)
                }))
              }
            >
              Precedente
            </button>
            <span>{data.page}</span>
            <button
              className="button button--ghost"
              type="button"
              disabled={data.page >= data.total_pages}
              onClick={() =>
                setFilters((current) => ({
                  ...current,
                  page: (current.page ?? 1) + 1
                }))
              }
            >
              Successiva
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
