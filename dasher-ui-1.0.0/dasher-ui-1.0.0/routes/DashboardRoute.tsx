//import node modules libraries
import { v4 as uuid } from "uuid";
import {
  IconFiles,
  IconShoppingBag,
  IconUsers,
  IconFile,
  IconLock,
  IconLayoutDashboard,
} from "@tabler/icons-react";

//import custom type
import { MenuItemType } from "types/menuTypes";

export const DashboardMenu: MenuItemType[] = [
  {
    id: uuid(),
    title: "Dashboard",
    link: "/",
    icon: <IconLayoutDashboard size={24} strokeWidth={1.5} />,
  },
  {
    id: uuid(),
    title: "Ecommerce",
    link: "/ecommerce",
    icon: <IconShoppingBag size={24} strokeWidth={1.5} />,
  },
  {
    id: uuid(),
    title: "Users",
    link: "/blog",
    icon: <IconUsers size={24} strokeWidth={1.5} />,
  }
];
