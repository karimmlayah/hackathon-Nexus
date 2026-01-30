import { ColumnDef } from "@tanstack/react-table";
import { Image } from "react-bootstrap";

export const TopProductColumns: ColumnDef<any>[] = [
    {
        accessorKey: "name",
        header: "Product",
        cell: ({ row }) => {
            return (
                <div className="d-flex align-items-center">
                    <Image
                        src={row.original.image}
                        alt=""
                        className="rounded-3"
                        width="40"
                        height="40"
                    />
                    <div className="ms-3">
                        <div className="fw-semibold text-truncate" style={{ maxWidth: '200px' }}>{row.original.name}</div>
                        <div className="small text-secondary">{row.original.category}</div>
                    </div>
                </div>
            );
        },
    },
    {
        accessorKey: "rating",
        header: "Rating",
        cell: ({ row }) => {
            return (
                <div className="d-flex align-items-center">
                    <span className="text-warning">★</span>
                    <span className="ms-1">{row.original.rating}</span>
                </div>
            );
        },
    },
    {
        accessorKey: "price",
        header: "Price",
    }
];
