"use client";
import React, { useState, useEffect } from "react";
//import node modules libraries
import { Card, CardHeader, CardFooter, Button } from "react-bootstrap";

//import custom components
import TanstackTable from "components/table/TanstackTable";
import { TopProductColumns } from "./TopProductColumns";

const ActiveProject = () => {
  const [data, setData] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchTopProducts = async () => {
      try {
        const response = await fetch("http://localhost:8000/api/dashboard/widgets");
        const result = await response.json();
        if (result.success) {
          setData(result.top_products);
        }
      } catch (error) {
        console.error("Failed to fetch top products", error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchTopProducts();
  }, []);

  return (
    <Card className="card-lg mb-6">
      <CardHeader className="border-bottom-0">
        <h5 className="mb-0">Best Rated Products</h5>
      </CardHeader>
      <div>
        {isLoading ? (
          <div className="text-center p-5">
            <div className="spinner-border text-primary spinner-border-sm" role="status"></div>
          </div>
        ) : (
          <TanstackTable data={data} columns={TopProductColumns} />
        )}
      </div>
      <CardFooter className=" border-dashed border-top text-center">
        <Button href="/ecommerce" variant="link">
          View All Products
        </Button>
      </CardFooter>
    </Card>
  );
};

export default ActiveProject;
