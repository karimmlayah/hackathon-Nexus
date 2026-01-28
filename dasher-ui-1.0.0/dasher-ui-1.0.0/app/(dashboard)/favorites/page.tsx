"use client";

import { useEffect, useState, Fragment } from "react";
import { Table, Button, Card, Row, Col } from "react-bootstrap";
import { IconHeartOff } from "@tabler/icons-react";

const FavoritesPage = () => {
    const [favorites, setFavorites] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchFavorites = async () => {
            const token = localStorage.getItem("finfit_token");
            if (!token) return;

            try {
                const response = await fetch("http://localhost:8000/api/user/favorites", {
                    headers: { "Authorization": `Bearer ${token}` }
                });
                if (response.ok) {
                    const data = await response.json();
                    setFavorites(data);
                }
            } catch (err) {
                console.error("Failed to fetch favorites");
            } finally {
                setLoading(false);
            }
        };
        fetchFavorites();
    }, []);

    return (
        <Fragment>
            <div className="mb-6 mt-4">
                <h2 className="mb-0">My Favorites</h2>
                <p>Your wishlist of products you love.</p>
            </div>

            <Row>
                <Col md={12}>
                    <Card className="border-0 shadow-sm">
                        <Card.Body className="p-0">
                            <Table responsive className="text-nowrap mb-0">
                                <thead className="table-light">
                                    <tr>
                                        <th>Product</th>
                                        <th>Price</th>
                                        <th>Action</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {favorites.length > 0 ? (
                                        favorites.map((item) => (
                                            <tr key={item.id}>
                                                <td className="align-middle">
                                                    <div className="d-flex align-items-center">
                                                        <img
                                                            src={item.product?.image_urls?.[0] || "https://via.placeholder.com/50"}
                                                            alt=""
                                                            className="rounded"
                                                            style={{ width: '40px', height: '40px', objectFit: 'cover' }}
                                                        />
                                                        <div className="ms-3">
                                                            <h5 className="mb-0 fs-6">{item.product?.name || "Unknown Product"}</h5>
                                                        </div>
                                                    </div>
                                                </td>
                                                <td className="align-middle text-dark fw-medium">
                                                    ${item.product?.price?.toFixed(2) || "0.00"}
                                                </td>
                                                <td className="align-middle">
                                                    <Button variant="outline-danger" size="sm">
                                                        <IconHeartOff size={16} /> Remove
                                                    </Button>
                                                </td>
                                            </tr>
                                        ))
                                    ) : (
                                        <tr>
                                            <td colSpan={3} className="text-center py-5 text-muted">
                                                {loading ? "Loading..." : "You haven't added any favorites yet."}
                                            </td>
                                        </tr>
                                    )}
                                </tbody>
                            </Table>
                        </Card.Body>
                    </Card>
                </Col>
            </Row>
        </Fragment>
    );
};

export default FavoritesPage;
