import os
import sys
import h3
import contextily as cx
import matplotlib.pyplot as plt
import pandas as pd
from shapely.geometry import box
import geopandas as gpd

# Thiết lập UTF-8 cho Windows Terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def render_cell_images(cells_parquet: str, output_img_dir: str, output_parquet: str):
    print(f"\n==========================================")
    print(f"🖼️ Đang render ảnh bản đồ 224x224 (No Labels)")
    print(f"🔷 Khung ô H3: {cells_parquet}")
    print(f"📁 Thư mục lưu ảnh: {output_img_dir}")
    print(f"==========================================")

    if not os.path.exists(cells_parquet):
        print(f"❌ Không tìm thấy file: {cells_parquet}")
        return

    df_cells = pd.read_parquet(cells_parquet)
    os.makedirs(output_img_dir, exist_ok=True)
    
    print(f"👉 Tổng số ô cần render ảnh: {len(df_cells)}")

    image_paths = []

    # CRS Web Mercator chuẩn cho tile bản đồ
    CRS_WEBMERCATOR = "EPSG:3857"

    for idx, row in df_cells.iterrows():
        cell_id = row["h3_index"]
        lat = row["centroid_lat"]
        lon = row["centroid_lon"]
        res = row.get("resolution", 8)
        
        img_filename = f"{cell_id}.png"
        img_full_path = os.path.join(output_img_dir, img_filename)
        
        # Bán kính crop quanh tâm ô theo hệ mét (Res 7 rộng hơn Res 8)
        # Res 7: crop bán kính ~1400m; Res 8: crop bán kính ~550m
        radius_m = 1400 if res == 7 else 550
        zoom_level = 15 if res == 7 else 16

        # Tạo điểm tâm và chuyển sang Web Mercator
        pt_gdf = gpd.GeoDataFrame(geometry=gpd.points_from_xy([lon], [lat]), crs="EPSG:4326").to_crs(CRS_WEBMERCATOR)
        center_x = pt_gdf.geometry.iloc[0].x
        center_y = pt_gdf.geometry.iloc[0].y

        # Tạo Figure chuẩn kích thước 224x224 pixels (dpi=100, figsize=(2.24, 2.24))
        fig, ax = plt.subplots(figsize=(2.24, 2.24), dpi=100)
        
        # Thiết lập khung hiển thị vuông cố định quanh tâm
        ax.set_xlim(center_x - radius_m, center_x + radius_m)
        ax.set_ylim(center_y - radius_m, center_y + radius_m)
        ax.axis("off") # Tắt toàn bộ viền tọa độ, trục số

        try:
            # Tải tile bản đồ không nhãn chữ (CartoDB Positron No Labels)
            cx.add_basemap(
                ax,
                crs=CRS_WEBMERCATOR,
                source=cx.providers.CartoDB.PositronNoLabels,
                zoom=zoom_level
            )
            # Lưu ảnh đúng 224x224 px
            plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
            plt.savefig(img_full_path, dpi=100, bbox_inches="tight", pad_inches=0)
            
            image_paths.append(img_full_path)
            print(f"[{idx+1}/{len(df_cells)}] Đã render: {img_filename}")
        except Exception as e:
            print(f"[{idx+1}/{len(df_cells)}] ⚠️ Lỗi khi tải tile cho {cell_id}: {e}")
            image_paths.append(None)
        finally:
            plt.close(fig)

    # Cập nhật cột image_path vào DataFrame
    df_cells["image_path"] = image_paths
    df_cells.to_parquet(output_parquet, index=False)

    print(f"\n🎉 HOÀN THÀNH B3 & HOÀN TẤT TOÀN BỘ TRACK B!")
    print(f"📁 Toàn bộ ảnh đã được lưu tại: {output_img_dir}")
    print(f"📁 Đã cập nhật image_path vào: {output_parquet}")

if __name__ == "__main__":
    in_cells = "data/processed/cells_xp.parquet"
    out_dir = "data/processed/cell_images"
    out_cells = "data/processed/cells_xp.parquet"

    if len(sys.argv) > 1:
        in_cells = sys.argv[1]
    if len(sys.argv) > 2:
        out_dir = sys.argv[2]
    if len(sys.argv) > 3:
        out_cells = sys.argv[3]

    render_cell_images(in_cells, out_dir, out_cells)