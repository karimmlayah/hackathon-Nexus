"use client";
import React, { useState, useEffect } from "react";
//import node modules libraries
import { IconUsers, IconUserShield, IconUser } from "@tabler/icons-react";
import { Row, Col, Card, CardBody } from "react-bootstrap";

//import custom components
import CustomProgressBar from "components/common/CustomProgressBar";

const TaskProgress = () => {
  const [stats, setStats] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await fetch("http://localhost:8000/api/dashboard/widgets");
        const result = await response.json();
        if (result.success) {
          setStats(result.user_stats);
        }
      } catch (error) {
        console.error("Failed to fetch user stats", error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchStats();
  }, []);

  if (isLoading) return (
    <Card className="card-lg mb-6">
      <CardBody className="text-center p-5">
        <div className="spinner-border text-primary" role="status"></div>
      </CardBody>
    </Card>
  );

  const superUserPercent = stats ? (stats.super_users / stats.total_users) * 100 : 0;
  const regularUserPercent = stats ? (stats.regular_users / stats.total_users) * 100 : 0;

  return (
    <Card className="card-lg mb-6">
      <CardBody>
        <div className="mb-4">
          <h5 className="mb-0">User Distribution</h5>
        </div>
        <div className="fs-1 fw-bold mb-3">{stats?.total_users || 0} Total</div>
        <div className="d-flex align-items-center gap-1 w-100 mb-4">
          <div style={{ width: `${superUserPercent}%` }}>
            <CustomProgressBar
              className="mb-2"
              now={100}
              style={{ height: "3px" }}
              variant="danger"
            />
          </div>
          <div style={{ width: `${regularUserPercent}%` }}>
            <CustomProgressBar
              className="mb-2"
              now={100}
              style={{ height: "3px" }}
              variant="info"
            />
          </div>
        </div>
        <div className="bg-gray-100 p-3 rounded-4">
          <Row className="g-3">
            <Col md={6}>
              <Card className="card-lg h-100">
                <CardBody className="text-center p-3">
                  <div className="icon-shape icon-lg bg-danger-subtle text-danger-emphasis rounded-pill">
                    <IconUserShield size={20} />
                  </div>
                  <div className="lh-1 mt-4">
                    <div className="fs-4 fw-bold mb-1">{stats?.super_users || 0}</div>
                    <div className="text-secondary small">Super Users</div>
                  </div>
                </CardBody>
              </Card>
            </Col>
            <Col md={6}>
              <Card className="card-lg h-100">
                <CardBody className="text-center p-3">
                  <div className="icon-shape icon-lg bg-info-subtle text-info-emphasis rounded-pill">
                    <IconUser size={20} />
                  </div>
                  <div className="lh-1 mt-4">
                    <div className="fs-4 fw-bold mb-1">{stats?.regular_users || 0}</div>
                    <div className="text-secondary small">Regular Users</div>
                  </div>
                </CardBody>
              </Card>
            </Col>
          </Row>
        </div>
      </CardBody>
    </Card>
  );
};

export default TaskProgress;

