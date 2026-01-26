//import node modules libraries
import { Container } from "react-bootstrap";

//import custom components
import Flex from "components/common/Flex";

const AuthLayout = ({ children }: { children: React.ReactNode }) => {
  return (
    <Flex
      tag='main'
      direction='column'
      justifyContent='center'
      className='vh-100'>
      <section>
        <Container>{children}</Container>
      </section>
      <div className='custom-container'>
        <span className='me-1'>Theme distributed by - </span>
        <a href='https://www.themewagon.com/' target='_blank' rel='noopener '>
          ThemeWagon
        </a>
      </div>
    </Flex>
  );
};

export default AuthLayout;
