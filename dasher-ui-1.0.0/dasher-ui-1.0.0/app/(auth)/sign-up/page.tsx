"use client";

//import node modules libraries
import { Fragment, useState } from "react";
import Feedback from "react-bootstrap/Feedback";
import {
    Row,
    Col,
    Image,
    Card,
    CardBody,
    Form,
    FormLabel,
    FormControl,
    Button,
} from "react-bootstrap";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
    IconBrandFacebookFilled,
    IconBrandGoogleFilled,
    IconEyeOff,
} from "@tabler/icons-react";

//import custom components
import Flex from "components/common/Flex";
import { getAssetPath } from "helper/assetPath";

const SignUp = () => {
    const router = useRouter();
    const searchParams = useSearchParams();
    const returnTo = searchParams.get("returnTo");

    const [name, setName] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [phone, setPhone] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    const handleSignUp = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError("");

        try {
            const response = await fetch("http://127.0.0.1:8000/api/register", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ name, email, password, phone }),
            });

            const data = await response.json();

            if (response.ok) {
                localStorage.setItem("finfit_token", data.access_token);
                if (returnTo) {
                    window.location.href = `${returnTo}?token=${data.access_token}`;
                } else {
                    alert("Registration successful! Please sign in.");
                    router.push("/sign-in");
                }
            } else {
                setError(data.detail || "Registration failed");
            }
        } catch (err) {
            setError("Server connection failed");
        } finally {
            setLoading(false);
        }
    };

    return (
        <Fragment>
            <Row className="mb-8">
                <Col xl={{ span: 4, offset: 4 }} md={12}>
                    <div className="text-center">
                        <Link
                            href="/"
                            className="fs-2 fw-bold d-flex align-items-center gap-2 justify-content-center mb-6"
                        >
                            <Image src={getAssetPath("/images/brand/logo/logo-icon.svg")} alt="FinFit" />
                            <span>FinFit</span>
                        </Link>
                        <h1 className="mb-1">Create Account</h1>
                        <p className="mb-0">
                            Already have an account?
                            <Link href="/sign-in" className="text-primary ms-1">
                                Sign In here
                            </Link>
                        </p>
                    </div>
                </Col>
            </Row>

            {/* Form Start */}
            <Row className="justify-content-center">
                <Col xl={5} lg={6} md={8}>
                    <Card className="card-lg mb-6">
                        <CardBody className="p-6">
                            <Form className="mb-6" onSubmit={handleSignUp}>
                                {error && <div className="alert alert-danger mb-4">{error}</div>}

                                <div className="mb-3">
                                    <FormLabel htmlFor="signupNameInput">Full Name</FormLabel>
                                    <FormControl
                                        type="text"
                                        id="signupNameInput"
                                        placeholder="Enter your name"
                                        value={name}
                                        onChange={(e) => setName(e.target.value)}
                                        required
                                    />
                                </div>

                                <div className="mb-3">
                                    <FormLabel htmlFor="signupEmailInput">Email</FormLabel>
                                    <FormControl
                                        type="email"
                                        id="signupEmailInput"
                                        placeholder="name@example.com"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        required
                                    />
                                </div>

                                <div className="mb-3">
                                    <FormLabel htmlFor="signupPhoneInput">Phone Number</FormLabel>
                                    <FormControl
                                        type="text"
                                        id="signupPhoneInput"
                                        placeholder="Enter phone number"
                                        value={phone}
                                        onChange={(e) => setPhone(e.target.value)}
                                    />
                                </div>

                                <div className="mb-3">
                                    <FormLabel htmlFor="signupPasswordInput">Password</FormLabel>
                                    <div className="password-field position-relative">
                                        <FormControl
                                            type="password"
                                            id="signupPasswordInput"
                                            value={password}
                                            onChange={(e) => setPassword(e.target.value)}
                                            required
                                        />
                                        <span>
                                            <IconEyeOff className="passwordToggler" size={16} />
                                        </span>
                                    </div>
                                </div>

                                <div className="d-grid mt-4">
                                    <Button variant="primary" type="submit" disabled={loading}>
                                        {loading ? "Creating Account..." : "Create Free Account"}
                                    </Button>
                                </div>
                            </Form>

                            <span>Sign up with your social network.</span>
                            <Flex justifyContent="between" className="mt-3 d-flex gap-2">
                                <Button href="#" variant="google" className="w-100">
                                    <span className="me-3">
                                        <IconBrandGoogleFilled size={18} />
                                    </span>
                                    Google
                                </Button>
                                <Button href="#" variant="facebook" className="w-100">
                                    <span className="me-3">
                                        <IconBrandFacebookFilled size={18} />
                                    </span>
                                    Facebook
                                </Button>
                            </Flex>
                        </CardBody>
                    </Card>
                </Col>
            </Row>
        </Fragment>
    );
};

export default SignUp;
