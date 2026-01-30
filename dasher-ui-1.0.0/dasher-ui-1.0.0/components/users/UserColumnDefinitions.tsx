import { ColumnDef } from "@tanstack/react-table";
import { Badge } from "react-bootstrap";
import { UserType } from "types/UserType";

export const userListColumns: ColumnDef<UserType>[] = [
    {
        accessorKey: "name",
        header: "Name",
        cell: ({ row }) => {
            return <span className="fw-semibold">{row.original.name}</span>;
        },
    },
    {
        accessorKey: "email",
        header: "Email",
    },
    {
        accessorKey: "role",
        header: "Role",
        cell: ({ row }) => {
            const role = row.original.role;
            let badgeColor = "secondary";
            if (role === "super_admin") badgeColor = "danger";
            if (role === "admin") badgeColor = "warning";
            if (role === "user") badgeColor = "info";

            return (
                <Badge bg={badgeColor} className="text-capitalize">
                    {role.replace('_', ' ')}
                </Badge>
            );
        },
    },
];
