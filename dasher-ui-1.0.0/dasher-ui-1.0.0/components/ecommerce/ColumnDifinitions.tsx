//import node module libraries
import React, { Fragment, useState } from "react";
import { ColumnDef } from "@tanstack/react-table";
import { IconEdit, IconEye, IconTrash } from "@tabler/icons-react";
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
      const productName = row.original.name;
      const [isExpanded, setIsExpanded] = useState(false);

      return (
        <div className="d-flex align-items-center">
          <Image
            src={row.original.imageSrc}
            alt=""
            className="rounded-3"
            width="56"
          />
          <div
            className="ms-3 d-flex flex-column"
            style={{
              minWidth: isExpanded ? '500px' : '200px',
              maxWidth: isExpanded ? 'none' : '200px',
              cursor: 'pointer',
              transition: 'all 0.3s ease'
            }}
            onClick={() => setIsExpanded(!isExpanded)}
          >
            <span
              className={`text-inherit fw-semibold ${isExpanded ? 'text-wrap' : 'text-truncate'}`}
              style={{ width: '100%' }}
              title={isExpanded ? "Click to collapse" : productName}
            >
              {productName}
            </span>
          </div>
        </div>
      );
    },
  },
  {
    accessorKey: "description",
    header: "Description",
    cell: ({ row }) => {
      const desc = row.original.description || "";
      const [isDescExpanded, setIsDescExpanded] = useState(false);
      return (
        <div
          className="ms-3 d-flex flex-column"
          style={{
            minWidth: isDescExpanded ? '500px' : '150px',
            maxWidth: isDescExpanded ? 'none' : '150px',
            cursor: 'pointer',
            transition: 'all 0.3s ease'
          }}
          onClick={() => setIsDescExpanded(!isDescExpanded)}
        >
          <span
            className={`text-inherit ${isDescExpanded ? 'text-wrap' : 'text-truncate'}`}
            title={isDescExpanded ? "Click to collapse" : desc}
          >
            {desc}
          </span>
        </div>
      );
    }
  },
  {
    accessorKey: "category",
    header: "Category",
  },
  {
    accessorKey: "brand",
    header: "Brand",
  },
  {
    accessorKey: "price",
    header: "Price",
  },
  {
    accessorKey: "rating",
    header: "Rating",
    cell: ({ row }) => {
      return (
        <div className="d-flex align-items-center">
          <span className="text-warning">★</span>
          <span className="ms-1">{row.original.rating || "N/A"}</span>
        </div>
      );
    }
  },
  {
    accessorKey: "availability",
    header: "Availability",
    cell: ({ row }) => {
      const availability = row.original.availability || "Unknown";
      const isInStock = availability.toLowerCase().includes("in stock");
      return (
        <Badge
          bg={isInStock ? "success-subtle" : "danger-subtle"}
          text={isInStock ? "success-emphasis" : "danger-emphasis"}
          pill={true}
        >
          {availability}
        </Badge>
      );
    },
  },
  {
    accessorKey: "",
    header: "Action",
    cell: ({ row }) => {
      return (
        <Fragment>
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

