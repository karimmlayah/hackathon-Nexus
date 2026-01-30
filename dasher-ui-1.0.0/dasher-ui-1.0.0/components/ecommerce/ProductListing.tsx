"use client";
//import node modules libraries
import React, { useState, useEffect } from "react";
import {
  Row,
  Col,
  Card,
  CardHeader,
  FormControl,
  Button,
  Dropdown,
  DropdownToggle,
  DropdownMenu,
  DropdownItem,
} from "react-bootstrap";

//import custom components
import Flex from "components/common/Flex";
import TanstackTable from "components/table/TanstackTable";
import { productListColumns } from "./ColumnDifinitions";
//import custom types
import { ProductListType } from "types/EcommerceType";

const ProductListing = () => {
  const [data, setData] = useState<ProductListType[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchProducts = async () => {
      try {
        const response = await fetch("http://localhost:8000/products?limit=100");
        const result = await response.json();

        if (result.products) {
          const mappedData: ProductListType[] = result.products.map((p: any) => ({
            id: p.id.toString(),
            name: p.name,
            category: p.category || "General",
            brand: p.name.split(' ')[0], // Heuristic: First word as brand
            addedDate: "Recently", // API doesn't provide this yet
            price: p.price,
            price_original: p.price_original,
            price_numeric: p.price_numeric,
            currency: p.currency,
            description: p.description,
            rating: p.rating || 0,
            availability: p.availability || "Out of Stock",
            imageSrc: p.image || "/images/ecommerce/product-1.jpg"
          }));
          setData(mappedData);
        }
      } catch (error) {
        console.error("Failed to fetch products", error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchProducts();
  }, []);
  return (
    <Row>
      <Col>
        <Card className="card-lg" id="productList">
          <CardHeader className="border-bottom-0">
            <Row className="g-4">
              <Col lg={4}>
                <FormControl
                  type="search"
                  className="listjs-search"
                  placeholder="Search"
                />
              </Col>
              <Col lg={8} className="d-flex justify-content-end">
                <Flex alignItems="center" breakpoint="lg" className="gap-2">
                  <div>
                    <Button variant="white">More Filter</Button>
                  </div>
                </Flex>
              </Col>
            </Row>
          </CardHeader>

          {/* Product List Table */}
          {isLoading ? (
            <div className="text-center p-5">
              <div className="spinner-border text-primary" role="status">
                <span className="visually-hidden">Loading...</span>
              </div>
            </div>
          ) : (
            <TanstackTable
              data={data}
              columns={productListColumns}
              pagination={true}
              isSortable
            />
          )}
        </Card>
      </Col>
    </Row>
  );
};

export default ProductListing;
