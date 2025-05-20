import React from "react";
import { Routes, Route } from "react-router-dom";
import "./App.scss";

import Home from "./App/Home";
import List from "./App/List";
import AboutUs from "./App/AboutUs";
import Category from "./App/Category";
import Images from "./App/Images";
import Tabbar from "./App/Tabbar";

const sortShopList = (shopList: Pwamap.ShopData[]) => {
  return shopList.sort((item1, item2) => {
    const date1 = Date.parse(item1["タイムスタンプ"]);
    const date2 = Date.parse(item2["タイムスタンプ"]);
    if (isNaN(date1) || isNaN(date2)) {
      console.warn("Invalid timestamp:", item1["タイムスタンプ"], item2["タイムスタンプ"]);
      return 0;
    }
    return date2 - date1;
  });
};

const App = () => {
  const [shopList, setShopList] = React.useState<Pwamap.ShopData[]>([]);

  React.useEffect(() => {
    fetch(`${process.env.PUBLIC_URL || ""}/data.json?timestamp=${new Date().getTime()}`)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTPエラー: ステータス ${response.status}`);
        }
        return response.json();
      })
      .then((data: Pwamap.ShopData[]) => {
        const nextShopList = data
          .filter((feature) => {
            if (!feature["緯度"] || !feature["経度"] || !feature["スポット名"]) {
              return false;
            }
            const latLongRegex = /^-?[0-9]+(\.[0-9]+)?$/;
            return latLongRegex.test(String(feature["緯度"])) && latLongRegex.test(String(feature["経度"]));
          })
          .map((feature, index) => ({
            index,
            ...feature,
          }));
        setShopList(sortShopList(nextShopList));
      })
      .catch((error) => {
        console.error("フェッチエラー:", error);
      });
  }, []);

  return (
    <div className="app">
      <div className="app-body">
        <Routes>
          <Route path="/" element={<Home data={shopList} />} />
          <Route path="/list" element={<List data={shopList} />} />
          <Route path="/category" element={<Category data={shopList} />} />
          <Route path="/images" element={<Images data={shopList} />} />
          <Route path="/about" element={<AboutUs />} />
        </Routes>
      </div>
      <div className="app-footer">
        <Tabbar />
      </div>
    </div>
  );
};

export default App;
