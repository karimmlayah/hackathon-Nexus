//import custom components
import Header from "layouts/header/Header";
import Sidebar from "layouts/Sidebar";

interface DashboardProps {
  children: React.ReactNode;
}

const DashboardLayout: React.FC<DashboardProps> = ({ children }) => {
  return (
    <div>
      <Sidebar hideLogo={false} containerId='miniSidebar' />
      <div id='content' className='position-relative h-100'>
        <Header />
        <div className='custom-container'>{children}</div>
      </div>
    </div>
  );
};

export default DashboardLayout;
