"use client";
import React, { useState, useEffect } from "react";
import { Row, Col, Card, FormControl } from "react-bootstrap";
import TanstackTable from "components/table/TanstackTable";
import { userListColumns } from "./UserColumnDefinitions";
import { UserType } from "types/UserType";

const UserListing = () => {
    const [data, setData] = useState<UserType[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const fetchUsers = async () => {
            try {
                const response = await fetch("http://localhost:8000/api/users");
                const result = await response.json();
                if (result.success) {
                    setData(result.users);
                }
            } catch (error) {
                console.error("Failed to fetch users", error);
            } finally {
                setIsLoading(false);
            }
        };

        fetchUsers();
    }, []);

    return (
        <Row>
            <Col>
                <Card className="card-lg">
                    <Card.Header className="border-bottom-0">
                        <Row className="g-4">
                            <Col lg={4}>
                                <FormControl
                                    type="search"
                                    className="listjs-search"
                                    placeholder="Search Users"
                                />
                            </Col>
                        </Row>
                    </Card.Header>

                    {isLoading ? (
                        <div className="text-center p-5">
                            <div className="spinner-border text-primary" role="status">
                                <span className="visually-hidden">Loading...</span>
                            </div>
                        </div>
                    ) : (
                        <TanstackTable
                            data={data}
                            columns={userListColumns}
                            pagination={true}
                            isSortable
                        />
                    )}
                </Card>
            </Col>
        </Row>
    );
};

export default UserListing;
