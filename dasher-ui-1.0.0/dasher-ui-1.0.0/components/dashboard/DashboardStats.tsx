"use client";
//import node modules libraries
import { useState, useEffect } from "react";
import { Col, Card, CardBody, Spinner } from "react-bootstrap";

//import required data files
import { DashboardStatsData } from "data/DashboardData";

const DashboardStats = () => {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await fetch("http://localhost:8000/api/stats");
        const data = await response.json();
        setStats(data);
      } catch (error) {
        console.error("Error fetching stats:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
  }, []);

  if (loading) {
    return (
      <div className="text-center w-100 py-5">
        <Spinner animation="border" variant="primary" />
        <p className="mt-2 text-muted">Loading Qdrant Stats...</p>
      </div>
    );
  }

  // Map backend stats to the UI items defined in DashboardStatsData
  const dynamicStats = DashboardStatsData.map((stat, index) => {
    let newValue = stat.value;
    let newBottomValue = stat.bottomValue;
    let newTitle = stat.title;

    if (stats) {
      if (index === 0) { // Total Projects -> Total Products
        newTitle = "Total Products";
        newValue = (stats.total_products ?? 0).toString();
        newBottomValue = "from Qdrant";
      } else if (index === 1) { // Task -> Categories
        newTitle = "Categories";
        newValue = (stats.total_categories ?? 0).toString();
        newBottomValue = "Unique counts";
      } else if (index === 2) { // Members -> Brands
        newTitle = "Brands";
        newValue = (stats.total_brands ?? 0).toString();
        newBottomValue = "Featured";
      } else if (index === 3) { // Productivity -> In Stock
        newTitle = "Products In Stock";
        const inStock = stats.in_stock ?? 0;
        const total = stats.total_products ?? 1;
        newValue = inStock.toString();
        newBottomValue = ((inStock / total) * 100).toFixed(0) + "%";
        stat.description = "Availability";
      }
    }

    return {
      ...stat,
      title: newTitle,
      value: newValue,
      bottomValue: newBottomValue,
    };
  });

  return (
    <>
      {dynamicStats.map((stat) => (
        <Col xl={3} md={6} key={stat.id}>
          <Card className={`card-lg ${stat.bgColor}`}>
            <CardBody className="d-flex flex-column gap-8">
              <div className="d-flex justify-content-between align-items-center">
                <div>
                  <div className="fw-semibold">{stat.title}</div>
                </div>
                <div className={`${stat.textColor}`}>{stat.icon}</div>
              </div>
              <div className="lh-1 d-flex flex-column gap-3">
                <div className="fs-1 fw-bold">{stat.value}</div>
                <p className="mb-0">
                  <span className={`me-1 ${stat.textColor}`}>
                    {stat.bottomValue}
                  </span>
                  <span className="text-secondary">{stat.description}</span>
                </p>
              </div>
            </CardBody>
          </Card>
        </Col>
      ))}
    </>
  );
};

export default DashboardStats;
