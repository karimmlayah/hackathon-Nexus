//import node module libraries
import { Fragment } from "react";
import { Metadata } from "next";

//import custom components
import ProductListing from "components/ecommerce/ProductListing";
import EcommerceHeader from "components/ecommerce/EcommerceHeader";

export const metadata: Metadata = {
  title: "Products | FinFit - Responsive Bootstrap 5 Admin Dashboard",
  description: "FinFit - Responsive Bootstrap 5 Admin Dashboard",
};

const Ecommerce = () => {
  return (
    <Fragment>
      <EcommerceHeader />
      <ProductListing />
    </Fragment>
  );
};

export default Ecommerce;

