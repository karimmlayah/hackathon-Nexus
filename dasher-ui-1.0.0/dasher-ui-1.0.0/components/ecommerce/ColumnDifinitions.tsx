//import node module libraries
import { Fragment } from "react";
import { ColumnDef } from "@tanstack/react-table";
import { IconEdit, IconEye, IconTrash, IconShoppingCart, IconHeart } from "@tabler/icons-react";
import { Badge, Button, Image } from "react-bootstrap";
import Link from "next/link";

//import custom types
import { ProductListType } from "types/EcommerceType";

//import custom components
import FinFitTippy from "components/common/FinFitTippy";
import Checkbox from "components/table/Checkbox";

export const productListColumns: ColumnDef<ProductListType>[] = [
  {
    id: "select",
    header: ({ table }) => {
      return (
        <Checkbox
          {...{
            checked: table.getIsAllRowsSelected(),
            indeterminate: table.getIsSomeRowsSelected(),
            onChange: table.getToggleAllRowsSelectedHandler(),
          }}
        />
      );
    },
    cell: ({ row }) => (
      <div>
        <Checkbox
          {...{
            checked: row.getIsSelected(),
            disabled: !row.getCanSelect(),
            indeterminate: row.getIsSomeSelected(),
            onChange: row.getToggleSelectedHandler(),
          }}
        />
      </div>
    ),
  },
  {
    accessorKey: "name",
    header: "Product",
    cell: ({ row }) => {
      return (
        <div className="d-flex align-items-center">
          <Image
            src={row.original.imageSrc}
            alt=""
            className="rounded-3"
            width="56"
          />
          <div className="ms-3 d-flex flex-column">
            <Link href="#!" className="text-inherit fw-semibold">
              Transparent Sunglasses
            </Link>
          </div>
        </div>
      );
    },
  },
  {
    accessorKey: "category",
    header: "Category",
  },
  {
    accessorKey: "addedDate",
    header: "Added Date",
  },
  {
    accessorKey: "price",
    header: "Price",
  },
  {
    accessorKey: "quantity",
    header: "Quantity",
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => {
      const statusText = row.original.status;
      return (
        <Badge
          bg={`${statusText === "Active" ? "success-subtle" : "danger-subtle"}`}
          text={`${statusText === "Active" ? "success-emphasis" : "danger-emphasis"
            }`}
          pill={true}
        >
          {statusText}
        </Badge>
      );
    },
  },
  {
    accessorKey: "",
    header: "Action",
    cell: ({ row }) => {
      const handleAddToCart = async () => {
        const token = localStorage.getItem("finfit_token");
        if (!token) {
          alert("Please login first");
          return;
        }
        try {
          const response = await fetch(`http://localhost:8000/api/user/cart?product_id=${row.original.id}`, {
            method: "POST",
            headers: { "Authorization": `Bearer ${token}` }
          });
          if (response.ok) alert("Added to cart!");
        } catch (err) { alert("Failed to add to cart"); }
      };

      const handleAddToFavorites = async () => {
        const token = localStorage.getItem("finfit_token");
        if (!token) {
          alert("Please login first");
          return;
        }
        try {
          const response = await fetch(`http://localhost:8000/api/user/favorites?product_id=${row.original.id}`, {
            method: "POST",
            headers: { "Authorization": `Bearer ${token}` }
          });
          if (response.ok) alert("Added to favorites!");
        } catch (err) { alert("Failed to add to favorites"); }
      };

      return (
        <Fragment>
          <FinFitTippy content="Add to Cart">
            <Button
              onClick={handleAddToCart}
              variant="ghost btn-icon"
              size="sm"
              className="rounded-circle text-primary"
            >
              <IconShoppingCart size={16} />
            </Button>
          </FinFitTippy>
          <FinFitTippy content="Add to Favorites">
            <Button
              onClick={handleAddToFavorites}
              variant="ghost btn-icon"
              size="sm"
              className="rounded-circle text-danger"
            >
              <IconHeart size={16} />
            </Button>
          </FinFitTippy>
          <FinFitTippy content="View">
            <Button
              href=""
              variant="ghost btn-icon"
              size="sm"
              className="rounded-circle"
            >
              <IconEye size={16} />
            </Button>
          </FinFitTippy>
          <FinFitTippy content="Edit">
            <Button
              href=""
              variant="ghost btn-icon"
              size="sm"
              className="rounded-circle"
            >
              <IconEdit size={16} />
            </Button>
          </FinFitTippy>
          <FinFitTippy content="Delete">
            <Button
              href=""
              variant="ghost btn-icon"
              size="sm"
              className="rounded-circle"
            >
              <IconTrash size={16} />
            </Button>
          </FinFitTippy>
        </Fragment>
      );
    },
  },
];

