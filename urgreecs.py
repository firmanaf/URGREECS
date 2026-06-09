# -*- coding: utf-8 -*-

from qgis.PyQt.QtCore import QCoreApplication, QVariant

from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterNumber,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterFolderDestination,
    QgsProcessingParameterField,
    QgsProcessingException,
    QgsField,
    QgsFeature,
    QgsFeatureSink,
    QgsGeometry,
    QgsPointXY,
    QgsRectangle,
    QgsWkbTypes,
    QgsCoordinateTransform,
    QgsSpatialIndex
)

import os
import csv
import math


class URGREECSUrbanGreenEquityAnalytics330300(QgsProcessingAlgorithm):

    BUILDINGS = 'BUILDINGS'
    BLOCKS = 'BLOCKS'
    CHM = 'CHM'
    POP_TOTAL = 'POP_TOTAL'
    POP_BABY = 'POP_BABY'
    POP_WOMEN = 'POP_WOMEN'
    POP_ELDERLY = 'POP_ELDERLY'
    RTH = 'RTH'
    ADMIN = 'ADMIN'
    ADMIN_NAME_FIELD = 'ADMIN_NAME_FIELD'
    BUFFER = 'BUFFER'

    OUT_BUILDINGS = 'OUT_BUILDINGS'
    OUT_BLOCKS = 'OUT_BLOCKS'
    OUT_ADMIN = 'OUT_ADMIN'
    OUT_BLOCK_CSV = 'OUT_BLOCK_CSV'
    OUT_ADMIN_CSV = 'OUT_ADMIN_CSV'
    OUT_PNG_FOLDER = 'OUT_PNG_FOLDER'

    def tr(self, text):
        return QCoreApplication.translate('Processing', text)

    def createInstance(self):
        return URGREECSUrbanGreenEquityAnalytics330300()

    def name(self):
        return 'urgreecs'

    def displayName(self):
        return self.tr('URGREECS 3-30-300')

    def shortHelpString(self):
        return self.tr(
            "<p><b>Created By: Firman Afrianto, Maya Safira</b></p>"
            "<p><b>URGREECS: Urban Green Equity Analytics 3-30-300</b> is a QGIS Processing tool "
            "for evaluating urban greenery, green accessibility, and spatial equity through an integrated "
            "3-30-300 framework. It combines building-level tree proximity, block-level canopy adequacy, "
            "300 meter access to public green space, vulnerable population exposure, and optional kelurahan "
            "or administrative aggregation.</p>"

            "<p><b>Purpose</b></p>"
            "<p>This algorithm supports evidence-based urban green planning, green infrastructure prioritization, "
            "environmental justice assessment, climate-sensitive planning, neighborhood health diagnostics, "
            "and administrative green equity reporting.</p>"

            "<p><b>Inputs</b></p>"
            "<ul>"
            "<li><b>Building footprints or points</b>: used for 3-tree proxy and building-level 300 meter access.</li>"
            "<li><b>Urban blocks</b>: used for 30 percent canopy cover, population exposure, and integrated green equity classification.</li>"
            "<li><b>Canopy Height Model (CHM)</b>: raster in meters. Pixels with values ≥ 3 m are treated as tree-canopy pixels.</li>"
            "<li><b>Total population raster</b>: population count per pixel.</li>"
            "<li><b>Baby population raster</b> optional: baby or young-child population count per pixel.</li>"
            "<li><b>Women population raster</b> optional: women population count per pixel.</li>"
            "<li><b>Elderly population raster</b> optional: elderly population count per pixel.</li>"
            "<li><b>RTH / public parks / public green spaces</b>: polygon or point layer representing accessible green spaces.</li>"
            "<li><b>Kelurahan/admin boundary</b> optional: polygon layer for administrative aggregation and policy-ready reporting.</li>"
            "<li><b>Tree search buffer</b>: buffer distance around buildings. Default is 30 meters.</li>"
            "</ul>"

            "<p><b>Processing Logic</b></p>"
            "<ol>"
            "<li><b>3 Trees</b>: each building is buffered, the roof/building footprint is removed, "
            "and CHM pixels ≥ 3 m are counted inside the outer buffer.</li>"
            "<li><b>30 Percent Green</b>: each block is overlaid with CHM to estimate canopy area and green cover percentage.</li>"
            "<li><b>300 Meter Access</b>: building and block distances to the nearest RTH/public park are calculated using a 300 m threshold.</li>"
            "<li><b>Population Service</b>: total and vulnerable population rasters are summed inside each block.</li>"
            "<li><b>Green Equity</b>: canopy deficit, access deficit, and vulnerable unserved exposure are combined into an equity score.</li>"
            "<li><b>Kelurahan/Admin Aggregation</b>: block results are summarized to administrative boundaries when the admin layer is provided.</li>"
            "</ol>"

            "<p><b>Output Datasets</b></p>"
            "<ul>"
            "<li><b>Output Buildings</b>: building layer with tree-pixel count, 3-tree status, distance to RTH, and 300 m access status.</li>"
            "<li><b>Output Blocks</b>: block layer with green cover, population, vulnerable population, access, equity score, and priority class.</li>"
            "<li><b>Output Admin</b>: optional kelurahan/admin layer with aggregated green equity indicators.</li>"
            "<li><b>CSV Block Result</b>: tabular export of block indicators.</li>"
            "<li><b>CSV Admin Result</b>: tabular export of administrative indicators.</li>"
            "<li><b>PNG Insight Folder</b>: modern charts and map-based insight graphics.</li>"
            "</ul>"

            "<p><b>Key Output Fields</b></p>"
            "<ul>"
            "<li><code>tree_px30</code>: CHM pixels ≥ 3 m around building buffer excluding roof/building footprint.</li>"
            "<li><code>ok_3tree</code>: 1 if tree_px30 ≥ 3, otherwise 0.</li>"
            "<li><code>green_pct</code>: block canopy cover percentage, capped to 0-100%.</li>"
            "<li><code>ok_30pct</code>: 1 if green_pct ≥ 30%, otherwise 0.</li>"
            "<li><code>dist_rth</code>: distance to nearest public green space.</li>"
            "<li><code>ok_300m</code>: 1 if distance ≤ 300 m, otherwise 0.</li>"
            "<li><code>pop_vuln</code>: total vulnerable population from baby, women, and elderly rasters.</li>"
            "<li><code>vuln_unserv</code>: vulnerable population not served by 300 m access.</li>"
            "<li><code>eq_score</code>: green equity priority score from canopy deficit, access deficit, and vulnerable exposure.</li>"
            "<li><code>eq_class</code>: Green Equity Secured, Low, Moderate, High, or Very High Equity Priority.</li>"
            "<li><code>main_prob</code>: dominant planning problem.</li>"
            "<li><code>rec_action</code>: recommended green infrastructure action.</li>"
            "</ul>"

            "<p><b>PNG Insight Outputs</b></p>"
            "<ul>"
            "<li>Modern scorecard dashboard.</li>"
            "<li>Compliance charts for 3-tree, 30% green, and 300 m access.</li>"
            "<li>Population served/unserved and vulnerable population served/unserved charts.</li>"
            "<li>Integrated block class and green equity priority charts.</li>"
            "<li>Maps of green cover, access, unserved population, vulnerable exposure, block equity class, and admin priority.</li>"
            "<li>Top priority block and kelurahan/admin rankings.</li>"
            "</ul>"

            "<p><b>Important Notes</b></p>"
            "<ul>"
            "<li>Use projected CRS in meters for building, block, RTH, and admin layers.</li>"
            "<li>CHM and population rasters should overlap the study area.</li>"
            "<li>The 3-tree indicator is a canopy-pixel proxy, not an individual tree-crown inventory.</li>"
            "<li>RTH accessibility is measured by Euclidean distance from centroid. It is not yet network walking distance.</li>"
            "<li>Optional vulnerable population rasters allow the tool to shift from green access analysis into green equity analysis.</li>"
            "</ul>"

            "<p><b>Dependencies</b></p>"
            "<ul>"
            "<li>Core QGIS Processing and PyQGIS libraries.</li>"
            "<li>Matplotlib is required for PNG insight generation. If unavailable, spatial layers and CSV outputs are still produced.</li>"
            "</ul>"
        )

    def initAlgorithm(self, config=None):

        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.BUILDINGS,
                self.tr('Building footprints or building points'),
                [QgsProcessing.TypeVectorPolygon, QgsProcessing.TypeVectorPoint]
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.BLOCKS,
                self.tr('Urban blocks (Polygon)'),
                [QgsProcessing.TypeVectorPolygon]
            )
        )

        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.CHM,
                self.tr('Canopy Height Model, CHM raster [m]')
            )
        )

        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.POP_TOTAL,
                self.tr('Total population raster, population per pixel')
            )
        )

        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.POP_BABY,
                self.tr('Optional baby / young-child population raster'),
                optional=True
            )
        )

        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.POP_WOMEN,
                self.tr('Optional women population raster'),
                optional=True
            )
        )

        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.POP_ELDERLY,
                self.tr('Optional elderly population raster'),
                optional=True
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.RTH,
                self.tr('RTH / public parks / public green spaces'),
                [QgsProcessing.TypeVectorPolygon, QgsProcessing.TypeVectorPoint]
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.ADMIN,
                self.tr('Optional kelurahan / administrative boundary'),
                [QgsProcessing.TypeVectorPolygon],
                optional=True
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.ADMIN_NAME_FIELD,
                self.tr('Optional admin name field'),
                parentLayerParameterName=self.ADMIN,
                type=QgsProcessingParameterField.Any,
                optional=True
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.BUFFER,
                self.tr('Tree search buffer around building, meter'),
                QgsProcessingParameterNumber.Double,
                defaultValue=30.0,
                minValue=0.0
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUT_BUILDINGS,
                self.tr('Output Buildings - 3 Trees and 300 m Access')
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUT_BLOCKS,
                self.tr('Output Blocks - Green Equity 3-30-300')
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUT_ADMIN,
                self.tr('Output Admin - Green Equity Summary')
            )
        )

        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUT_BLOCK_CSV,
                self.tr('CSV Block Result'),
                fileFilter='CSV files (*.csv)'
            )
        )

        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUT_ADMIN_CSV,
                self.tr('CSV Admin Result'),
                fileFilter='CSV files (*.csv)'
            )
        )

        self.addParameter(
            QgsProcessingParameterFolderDestination(
                self.OUT_PNG_FOLDER,
                self.tr('PNG Insight Folder')
            )
        )

    # ------------------------------------------------------------------
    # Geometry and raster utilities
    # ------------------------------------------------------------------

    def _ensure_metric_crs(self, source, layer_name):
        if source and source.sourceCrs().isGeographic():
            raise QgsProcessingException(
                f'{layer_name} uses a geographic CRS. Please reproject it to a projected CRS in meters.'
            )

    def _safe_make_valid(self, geom):
        if geom is None or geom.isEmpty():
            return geom
        try:
            if not geom.isGeosValid():
                geom = geom.makeValid()
        except Exception:
            pass
        return geom

    def _clone_fields_with_additions(self, source_fields, additions):
        fields = source_fields
        for field_name, field_type in additions:
            if fields.indexFromName(field_name) == -1:
                fields.append(QgsField(field_name, field_type))
        return fields

    def _copy_original_attrs(self, out_feat, in_feat):
        attrs = in_feat.attributes()
        for idx, val in enumerate(attrs):
            try:
                out_feat.setAttribute(idx, val)
            except Exception:
                pass

    def _transform_geometry(self, geom, src_crs, dst_crs, context):
        if geom is None or geom.isEmpty():
            return geom
        g = QgsGeometry(geom)
        if src_crs != dst_crs:
            tr = QgsCoordinateTransform(src_crs, dst_crs, context.transformContext())
            g.transform(tr)
        return g

    def _collect_rth_points(self, rth_source):
        rth_geoms = []
        for f in rth_source.getFeatures():
            g = f.geometry()
            if g is None or g.isEmpty():
                continue
            if g.type() == QgsWkbTypes.PointGeometry:
                rth_geoms.append(g)
            else:
                rth_geoms.append(g.centroid())
        return rth_geoms

    def _nearest_distance(self, geom, target_geoms):
        if geom is None or geom.isEmpty() or not target_geoms:
            return -1.0
        min_dist = None
        for tg in target_geoms:
            try:
                d = geom.distance(tg)
                if min_dist is None or d < min_dist:
                    min_dist = d
            except Exception:
                continue
        return float(min_dist) if min_dist is not None else -1.0

    def _raster_window_from_bbox(self, bbox, provider, raster_extent, px_w, px_h):
        bbox = QgsRectangle(bbox)
        bbox = bbox.intersect(raster_extent)
        if bbox.isEmpty():
            return None

        raster_width = provider.xSize()
        raster_height = provider.ySize()

        c_min = int(math.floor((bbox.xMinimum() - raster_extent.xMinimum()) / px_w))
        c_max = int(math.floor((bbox.xMaximum() - raster_extent.xMinimum()) / px_w))

        r_min = int(math.floor((raster_extent.yMaximum() - bbox.yMaximum()) / px_h))
        r_max = int(math.floor((raster_extent.yMaximum() - bbox.yMinimum()) / px_h))

        c_min = max(0, min(c_min, raster_width - 1))
        c_max = max(0, min(c_max, raster_width - 1))
        r_min = max(0, min(r_min, raster_height - 1))
        r_max = max(0, min(r_max, raster_height - 1))

        if c_max < c_min or r_max < r_min:
            return None

        cols = c_max - c_min + 1
        rows = r_max - r_min + 1

        x_min = raster_extent.xMinimum() + c_min * px_w
        x_max = raster_extent.xMinimum() + (c_max + 1) * px_w
        y_max = raster_extent.yMaximum() - r_min * px_h
        y_min = raster_extent.yMaximum() - (r_max + 1) * px_h

        return {
            'c_min': c_min,
            'r_min': r_min,
            'cols': cols,
            'rows': rows,
            'extent': QgsRectangle(x_min, y_min, x_max, y_max)
        }

    def _count_raster_pixels_ge(self, raster_layer, geom_src, geom_src_crs, threshold, context):
        if raster_layer is None or geom_src is None or geom_src.isEmpty():
            return 0, 0.0

        provider = raster_layer.dataProvider()
        raster_extent = provider.extent()
        raster_width = provider.xSize()
        raster_height = provider.ySize()

        if raster_width <= 0 or raster_height <= 0:
            return 0, 0.0

        px_w = raster_extent.width() / raster_width
        px_h = raster_extent.height() / raster_height
        px_area = abs(px_w * px_h)

        geom = self._transform_geometry(geom_src, geom_src_crs, raster_layer.crs(), context)
        geom = self._safe_make_valid(geom)

        if geom is None or geom.isEmpty():
            return 0, px_area

        window = self._raster_window_from_bbox(geom.boundingBox(), provider, raster_extent, px_w, px_h)
        if window is None:
            return 0, px_area

        block = provider.block(1, window['extent'], window['cols'], window['rows'])
        if block is None or not block.isValid():
            return 0, px_area

        count = 0

        for br in range(window['rows']):
            for bc in range(window['cols']):
                global_c = window['c_min'] + bc
                global_r = window['r_min'] + br

                x = raster_extent.xMinimum() + (global_c + 0.5) * px_w
                y = raster_extent.yMaximum() - (global_r + 0.5) * px_h

                if not geom.contains(QgsGeometry.fromPointXY(QgsPointXY(x, y))):
                    continue

                try:
                    if block.isNoData(br, bc):
                        continue
                except Exception:
                    pass

                try:
                    if float(block.value(br, bc)) >= threshold:
                        count += 1
                except Exception:
                    pass

        return int(count), float(px_area)

    def _sum_raster_inside_geom(self, raster_layer, geom_src, geom_src_crs, context):
        if raster_layer is None or geom_src is None or geom_src.isEmpty():
            return 0.0

        provider = raster_layer.dataProvider()
        raster_extent = provider.extent()
        raster_width = provider.xSize()
        raster_height = provider.ySize()

        if raster_width <= 0 or raster_height <= 0:
            return 0.0

        px_w = raster_extent.width() / raster_width
        px_h = raster_extent.height() / raster_height

        geom = self._transform_geometry(geom_src, geom_src_crs, raster_layer.crs(), context)
        geom = self._safe_make_valid(geom)

        if geom is None or geom.isEmpty():
            return 0.0

        window = self._raster_window_from_bbox(geom.boundingBox(), provider, raster_extent, px_w, px_h)
        if window is None:
            return 0.0

        block = provider.block(1, window['extent'], window['cols'], window['rows'])
        if block is None or not block.isValid():
            return 0.0

        total = 0.0

        for br in range(window['rows']):
            for bc in range(window['cols']):
                global_c = window['c_min'] + bc
                global_r = window['r_min'] + br

                x = raster_extent.xMinimum() + (global_c + 0.5) * px_w
                y = raster_extent.yMaximum() - (global_r + 0.5) * px_h

                if not geom.contains(QgsGeometry.fromPointXY(QgsPointXY(x, y))):
                    continue

                try:
                    if block.isNoData(br, bc):
                        continue
                except Exception:
                    pass

                try:
                    value = float(block.value(br, bc))
                    if value > 0:
                        total += value
                except Exception:
                    pass

        return float(total)

    # ------------------------------------------------------------------
    # Classification utilities
    # ------------------------------------------------------------------

    def _class_330300(self, ok_30, ok_300):
        if ok_30 == 1 and ok_300 == 1:
            return 'Optimal Green Access'
        if ok_30 == 1 and ok_300 == 0:
            return 'Green but Poor Access'
        if ok_30 == 0 and ok_300 == 1:
            return 'Accessible but Low Canopy'
        return 'Priority Deficit Area'

    def _equity_class(self, score):
        if score >= 80:
            return 'Very High Equity Priority'
        if score >= 60:
            return 'High Equity Priority'
        if score >= 40:
            return 'Moderate Equity Priority'
        if score >= 20:
            return 'Low Equity Priority'
        return 'Green Equity Secured'

    def _main_problem_and_action(self, canopy_def, access_def, vuln_exposure):
        if canopy_def >= 0.50 and access_def >= 0.50 and vuln_exposure >= 0.50:
            return 'Combined Green Equity Deficit', 'Priority green equity intervention'
        if vuln_exposure >= 0.60:
            return 'High Vulnerable Exposure', 'Target vulnerable groups with nearest green access improvement'
        if canopy_def >= access_def and canopy_def >= 0.40:
            return 'Low Canopy', 'Street tree intensification and block greening'
        if access_def >= 0.40:
            return 'Poor Access', 'Pocket park provision and RTH access improvement'
        return 'Relatively Secured', 'Maintain and protect existing green assets'

    def _compute_equity_score(self, green_pct, dist_rth, vuln_unserved, max_vuln_unserved):
        canopy_def = max(0.0, 30.0 - float(green_pct)) / 30.0
        canopy_def = max(0.0, min(canopy_def, 1.0))

        if dist_rth < 0:
            access_def = 1.0
        else:
            access_def = max(0.0, float(dist_rth) - 300.0) / 700.0
            access_def = max(0.0, min(access_def, 1.0))

        if max_vuln_unserved > 0:
            vuln_exposure = max(0.0, min(float(vuln_unserved) / max_vuln_unserved, 1.0))
        else:
            vuln_exposure = 0.0

        score = (0.35 * canopy_def + 0.30 * access_def + 0.35 * vuln_exposure) * 100.0
        return float(score), float(canopy_def), float(access_def), float(vuln_exposure)

    # ------------------------------------------------------------------
    # Plotting utilities
    # ------------------------------------------------------------------

    def _try_import_plotting(self):
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            from matplotlib.patches import Polygon as MplPolygon
            from matplotlib.collections import PatchCollection
            return plt, MplPolygon, PatchCollection
        except Exception:
            return None, None, None

    def _modern_fig(self, plt, figsize=(13.5, 7.5)):
        fig = plt.figure(figsize=figsize, dpi=190)
        fig.patch.set_facecolor('#f7fafc')
        return fig

    def _header(self, fig, title, subtitle=None):
        fig.text(0.045, 0.935, 'URGREECS | URBAN GREEN EQUITY ANALYTICS',
                 fontsize=9.5, fontweight='bold', color='#0f766e', alpha=0.95)
        fig.text(0.045, 0.89, title,
                 fontsize=22, fontweight='bold', color='#0f172a')
        if subtitle:
            fig.text(0.045, 0.855, subtitle,
                     fontsize=10.3, color='#475569')
        fig.text(0.045, 0.035,
                 'Created By: Firman Afrianto, Maya Safira',
                 fontsize=8.5, color='#64748b')

    def _beautify_axis(self, ax):
        ax.set_facecolor('#ffffff')
        ax.grid(axis='y', color='#e2e8f0', linewidth=0.8, alpha=0.85)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#cbd5e1')
        ax.spines['bottom'].set_color('#cbd5e1')
        ax.tick_params(colors='#334155', labelsize=9)

    def _save_bar(self, plt, path, title, labels, values, ylabel='Count', subtitle=None, horizontal=False):
        fig = self._modern_fig(plt)
        self._header(fig, title, subtitle)
        if horizontal:
            ax = fig.add_axes([0.25, 0.16, 0.69, 0.62])
            ax.barh(labels[::-1], values[::-1], color='#0f766e', edgecolor='white', linewidth=0.8)
            ax.set_xlabel(ylabel, fontsize=10, color='#334155')
            ax.grid(axis='x', color='#e2e8f0', linewidth=0.8, alpha=0.85)
        else:
            ax = fig.add_axes([0.08, 0.18, 0.87, 0.60])
            colors = ['#0f766e', '#ef4444', '#2563eb', '#f59e0b', '#7c3aed', '#14b8a6']
            bars = ax.bar(labels, values, color=[colors[i % len(colors)] for i in range(len(values))],
                          edgecolor='white', linewidth=1.2)
            ax.set_ylabel(ylabel, fontsize=10, color='#334155')
            maxv = max(values) if values else 0
            for bar, val in zip(bars, values):
                ax.text(bar.get_x() + bar.get_width()/2,
                        bar.get_height() + maxv * 0.02 if maxv else 0.02,
                        f'{val:,.0f}', ha='center', va='bottom',
                        fontsize=10, fontweight='bold', color='#0f172a')
        self._beautify_axis(ax)
        fig.savefig(path, bbox_inches='tight', facecolor=fig.get_facecolor())
        plt.close(fig)

    def _save_hist(self, plt, path, title, values, xlabel, subtitle=None, bins=20):
        vals = []
        for v in values:
            try:
                fv = float(v)
                if math.isfinite(fv):
                    vals.append(fv)
            except Exception:
                pass

        fig = self._modern_fig(plt)
        self._header(fig, title, subtitle)
        ax = fig.add_axes([0.08, 0.18, 0.87, 0.60])
        if vals:
            ax.hist(vals, bins=bins, color='#0f766e', edgecolor='white', linewidth=0.8, alpha=0.92)
            mean_val = sum(vals) / len(vals)
            ax.axvline(mean_val, linestyle='--', linewidth=1.8, color='#f97316')
            ax.text(mean_val, ax.get_ylim()[1] * 0.90, f'Mean {mean_val:,.2f}',
                    rotation=90, va='top', ha='right', fontsize=9,
                    color='#f97316', fontweight='bold')
        else:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes)
        ax.set_xlabel(xlabel, fontsize=10, color='#334155')
        ax.set_ylabel('Frequency', fontsize=10, color='#334155')
        self._beautify_axis(ax)
        fig.savefig(path, bbox_inches='tight', facecolor=fig.get_facecolor())
        plt.close(fig)

    def _save_scatter(self, plt, path, title, x_values, y_values, xlabel, ylabel, subtitle=None):
        xs, ys = [], []
        for x, y in zip(x_values, y_values):
            try:
                fx = float(x)
                fy = float(y)
                if math.isfinite(fx) and math.isfinite(fy) and fy >= 0:
                    xs.append(fx)
                    ys.append(fy)
            except Exception:
                pass

        fig = self._modern_fig(plt)
        self._header(fig, title, subtitle)
        ax = fig.add_axes([0.08, 0.18, 0.87, 0.60])
        if xs:
            ax.scatter(xs, ys, alpha=0.78, s=36, color='#2563eb', edgecolor='white', linewidth=0.4)
            ax.axvline(30, linestyle='--', linewidth=1.4, color='#0f766e', alpha=0.85)
            ax.axhline(300, linestyle='--', linewidth=1.4, color='#ef4444', alpha=0.85)
        else:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes)
        ax.set_xlabel(xlabel, fontsize=10, color='#334155')
        ax.set_ylabel(ylabel, fontsize=10, color='#334155')
        self._beautify_axis(ax)
        ax.grid(color='#e2e8f0', linewidth=0.8, alpha=0.85)
        fig.savefig(path, bbox_inches='tight', facecolor=fig.get_facecolor())
        plt.close(fig)

    def _save_scorecard(self, plt, path, stats):
        fig = self._modern_fig(plt, figsize=(14, 8))
        ax = fig.add_axes([0, 0, 1, 1])
        ax.axis('off')

        fig.text(0.045, 0.94, 'URGREECS | URBAN GREEN EQUITY ANALYTICS',
                 fontsize=10, fontweight='bold', color='#0f766e')
        fig.text(0.045, 0.885, 'Urban Green Equity 3-30-300 Dashboard',
                 fontsize=27, fontweight='bold', color='#0f172a')
        fig.text(0.045, 0.845,
                 'Tree proximity, canopy adequacy, public green access, vulnerable exposure, and administrative priority.',
                 fontsize=11, color='#475569')

        cards = [
            ('Buildings', f"{stats.get('n_buildings', 0):,.0f}", 'evaluated building units', '#0f766e'),
            ('3-Tree OK', f"{stats.get('pct_3tree_ok', 0):,.1f}%", 'building-level tree proxy', '#14b8a6'),
            ('Blocks', f"{stats.get('n_blocks', 0):,.0f}", 'evaluated blocks', '#2563eb'),
            ('30% Green OK', f"{stats.get('pct_30_ok', 0):,.1f}%", 'block canopy compliance', '#22c55e'),
            ('300 m Access OK', f"{stats.get('pct_300_ok', 0):,.1f}%", 'block access compliance', '#f97316'),
            ('Population Served', f"{stats.get('pct_pop_served', 0):,.1f}%", 'served by 300 m access', '#7c3aed'),
            ('Vulnerable Unserved', f"{stats.get('vuln_unserved', 0):,.0f}", 'baby, women, elderly', '#ef4444'),
            ('Very High Priority', f"{stats.get('very_high_blocks', 0):,.0f}", 'equity priority blocks', '#991b1b')
        ]

        x0s = [0.045, 0.285, 0.525, 0.765]
        y0s = [0.56, 0.30]
        k = 0
        for y0 in y0s:
            for x0 in x0s:
                title, value, subtitle, color = cards[k]
                rect = plt.Rectangle((x0, y0), 0.195, 0.19, facecolor='white',
                                     edgecolor='#e2e8f0', linewidth=1.0)
                ax.add_patch(rect)
                accent = plt.Rectangle((x0, y0), 0.012, 0.19, facecolor=color,
                                       edgecolor=color, linewidth=0)
                ax.add_patch(accent)
                fig.text(x0 + 0.024, y0 + 0.133, title, fontsize=11.5,
                         fontweight='bold', color='#334155')
                fig.text(x0 + 0.024, y0 + 0.072, value, fontsize=25,
                         fontweight='bold', color='#0f172a')
                fig.text(x0 + 0.024, y0 + 0.033, subtitle, fontsize=8.6,
                         color='#64748b')
                k += 1

        fig.text(0.045, 0.15, 'Planning interpretation',
                 fontsize=13, fontweight='bold', color='#0f172a')
        fig.text(0.045, 0.115,
                 'Very high priority areas combine canopy deficit, poor green access, and vulnerable population exposure. '
                 'These locations should be considered first for street-tree intensification, pocket parks, safe walking access, and targeted green-health interventions.',
                 fontsize=10, color='#475569')
        fig.text(0.045, 0.05, 'Created By: Firman Afrianto, Maya Safira',
                 fontsize=8.5, color='#64748b')

        fig.savefig(path, bbox_inches='tight', facecolor=fig.get_facecolor())
        plt.close(fig)

    def _geom_to_patches(self, geom, MplPolygon):
        patches = []
        if geom is None or geom.isEmpty():
            return patches
        try:
            polygons = geom.asMultiPolygon() if geom.isMultipart() else [geom.asPolygon()]
        except Exception:
            return patches
        for poly in polygons:
            if not poly:
                continue
            ring = poly[0]
            coords = [(p.x(), p.y()) for p in ring]
            if len(coords) >= 3:
                patches.append(MplPolygon(coords, closed=True))
        return patches

    def _plot_polygon_map(self, plt, MplPolygon, PatchCollection, path, title, subtitle, features,
                          value_key=None, class_key=None, numeric=False, legend_title=None,
                          fixed_min=None, fixed_max=None):
        fig = self._modern_fig(plt, figsize=(13.5, 8.2))
        self._header(fig, title, subtitle)
        ax = fig.add_axes([0.045, 0.095, 0.72, 0.73])
        side = fig.add_axes([0.79, 0.14, 0.17, 0.62])
        side.axis('off')

        patches, values, classes = [], [], []
        xmin = ymin = xmax = ymax = None

        for item in features:
            geom = item.get('geom')
            if geom is None or geom.isEmpty():
                continue
            bbox = geom.boundingBox()
            xmin = bbox.xMinimum() if xmin is None else min(xmin, bbox.xMinimum())
            ymin = bbox.yMinimum() if ymin is None else min(ymin, bbox.yMinimum())
            xmax = bbox.xMaximum() if xmax is None else max(xmax, bbox.xMaximum())
            ymax = bbox.yMaximum() if ymax is None else max(ymax, bbox.yMaximum())

            geom_patches = self._geom_to_patches(geom, MplPolygon)
            for p in geom_patches:
                patches.append(p)
                if numeric:
                    try:
                        values.append(float(item.get(value_key, 0)))
                    except Exception:
                        values.append(0.0)
                else:
                    classes.append(item.get(class_key, 'Unknown'))

        if not patches:
            ax.text(0.5, 0.5, 'No polygon geometry available', ha='center', va='center', transform=ax.transAxes)
            fig.savefig(path, bbox_inches='tight', facecolor=fig.get_facecolor())
            plt.close(fig)
            return

        if numeric:
            vals = values
            if value_key == 'green_pct':
                vals = [max(0.0, min(float(v), 100.0)) for v in vals]
                vmin, vmax = 0.0, 100.0
                cmap_name = 'Greens'
            else:
                vals_sorted = sorted(vals)
                vmin = fixed_min if fixed_min is not None else (min(vals_sorted) if vals_sorted else 0.0)
                if fixed_max is not None:
                    vmax = fixed_max
                elif len(vals_sorted) >= 20:
                    vmax = vals_sorted[int(0.95 * (len(vals_sorted) - 1))]
                    if vmax <= vmin:
                        vmax = max(vals_sorted)
                else:
                    vmax = max(vals_sorted) if vals_sorted else 1.0
                if vmax <= vmin:
                    vmax = vmin + 1.0
                cmap_name = 'YlOrRd' if ('unserv' in value_key or 'score' in value_key or 'priority' in value_key) else 'viridis'

            pc = PatchCollection(patches, cmap=cmap_name, edgecolor='#94a3b8', linewidth=0.15)
            pc.set_array(vals)
            pc.set_clim(vmin, vmax)
            ax.add_collection(pc)

            cax = fig.add_axes([0.79, 0.20, 0.025, 0.45])
            cb = fig.colorbar(pc, cax=cax)
            cb.ax.tick_params(labelsize=8, colors='#334155')
            cb.set_label(legend_title or value_key, fontsize=9, color='#334155')
            side.text(0.0, 0.95, legend_title or value_key, fontsize=11, fontweight='bold', color='#0f172a')
            side.text(0.0, 0.89, f'Display min: {vmin:,.2f}', fontsize=9, color='#475569')
            side.text(0.0, 0.84, f'Display max: {vmax:,.2f}', fontsize=9, color='#475569')
        else:
            palette = {
                'Optimal Green Access': '#0f766e',
                'Green but Poor Access': '#22c55e',
                'Accessible but Low Canopy': '#f59e0b',
                'Priority Deficit Area': '#ef4444',
                'Green Equity Secured': '#0f766e',
                'Low Equity Priority': '#84cc16',
                'Moderate Equity Priority': '#f59e0b',
                'High Equity Priority': '#f97316',
                'Very High Equity Priority': '#dc2626',
                'Within 300 m': '#2563eb',
                'Beyond 300 m': '#ef4444',
                'OK': '#0f766e',
                'Not OK': '#ef4444',
                'Unknown': '#94a3b8'
            }
            colors = [palette.get(c, '#94a3b8') for c in classes]
            pc = PatchCollection(patches, facecolor=colors, edgecolor='#94a3b8', linewidth=0.15)
            ax.add_collection(pc)

            counts = {}
            for c in classes:
                counts[c] = counts.get(c, 0) + 1

            side.text(0.0, 0.95, legend_title or 'Legend', fontsize=11, fontweight='bold', color='#0f172a')
            y = 0.88
            for cls, cnt in sorted(counts.items(), key=lambda kv: kv[0]):
                color = palette.get(cls, '#94a3b8')
                side.add_patch(plt.Rectangle((0.0, y - 0.017), 0.06, 0.032, facecolor=color,
                                             edgecolor='white', linewidth=0.5))
                side.text(0.075, y, cls, fontsize=8.0, color='#334155', va='center')
                side.text(0.075, y - 0.034, f'{cnt:,.0f} features', fontsize=7.2, color='#64748b', va='center')
                y -= 0.103

        if xmin is not None:
            dx = xmax - xmin
            dy = ymax - ymin
            pad = max(dx, dy) * 0.04 if max(dx, dy) > 0 else 1
            ax.set_xlim(xmin - pad, xmax + pad)
            ax.set_ylim(ymin - pad, ymax + pad)

        ax.set_aspect('equal', adjustable='box')
        ax.axis('off')
        ax.set_facecolor('#eef2f7')
        ax.annotate('N', xy=(0.95, 0.18), xytext=(0.95, 0.08), xycoords='axes fraction',
                    arrowprops=dict(facecolor='#0f172a', width=3, headwidth=10),
                    ha='center', va='center', fontsize=10, fontweight='bold', color='#0f172a')

        fig.savefig(path, bbox_inches='tight', facecolor=fig.get_facecolor())
        plt.close(fig)

    def _plot_building_map(self, plt, MplPolygon, PatchCollection, path, title, subtitle,
                           building_features, block_features=None, class_key='ok_3tree_label'):
        fig = self._modern_fig(plt, figsize=(13.5, 8.2))
        self._header(fig, title, subtitle)
        ax = fig.add_axes([0.045, 0.095, 0.72, 0.73])
        side = fig.add_axes([0.79, 0.14, 0.17, 0.62])
        side.axis('off')

        # Drawing every building point can be very slow and visually overcrowded.
        # For PNG map only, keep all failing points and sample OK points when the layer is very large.
        max_ok_points_to_draw = 25000
        if building_features and len(building_features) > 60000:
            bad_items = [it for it in building_features if it.get(class_key) != 'OK']
            ok_items = [it for it in building_features if it.get(class_key) == 'OK']
            if len(ok_items) > max_ok_points_to_draw:
                step = max(1, int(len(ok_items) / max_ok_points_to_draw))
                ok_items = ok_items[::step]
            building_features = ok_items + bad_items

        xmin = ymin = xmax = ymax = None

        if block_features:
            patches = []
            for item in block_features:
                geom = item.get('geom')
                if geom is None or geom.isEmpty():
                    continue
                bbox = geom.boundingBox()
                xmin = bbox.xMinimum() if xmin is None else min(xmin, bbox.xMinimum())
                ymin = bbox.yMinimum() if ymin is None else min(ymin, bbox.yMinimum())
                xmax = bbox.xMaximum() if xmax is None else max(xmax, bbox.xMaximum())
                ymax = bbox.yMaximum() if ymax is None else max(ymax, bbox.yMaximum())
                patches.extend(self._geom_to_patches(geom, MplPolygon))
            if patches:
                pc = PatchCollection(patches, facecolor='#e2e8f0', edgecolor='white', linewidth=0.18, alpha=0.75)
                ax.add_collection(pc)

        xs_ok, ys_ok, xs_bad, ys_bad = [], [], [], []
        for item in building_features:
            geom = item.get('geom')
            if geom is None or geom.isEmpty():
                continue
            pt_geom = geom if geom.type() == QgsWkbTypes.PointGeometry else geom.centroid()
            try:
                p = pt_geom.asPoint()
            except Exception:
                continue
            x, y = p.x(), p.y()
            xmin = x if xmin is None else min(xmin, x)
            ymin = y if ymin is None else min(ymin, y)
            xmax = x if xmax is None else max(xmax, x)
            ymax = y if ymax is None else max(ymax, y)
            if item.get(class_key) == 'OK':
                xs_ok.append(x)
                ys_ok.append(y)
            else:
                xs_bad.append(x)
                ys_bad.append(y)

        ax.scatter(xs_ok, ys_ok, s=8, color='#0f766e', alpha=0.60, linewidth=0)
        ax.scatter(xs_bad, ys_bad, s=10, color='#ef4444', alpha=0.84, linewidth=0)

        side.text(0.0, 0.95, 'Legend', fontsize=11, fontweight='bold', color='#0f172a')
        side.add_patch(plt.Rectangle((0.0, 0.86), 0.06, 0.035, facecolor='#0f766e', edgecolor='white'))
        side.text(0.075, 0.877, f'OK: {len(xs_ok):,.0f}', fontsize=9, color='#334155', va='center')
        side.add_patch(plt.Rectangle((0.0, 0.78), 0.06, 0.035, facecolor='#ef4444', edgecolor='white'))
        side.text(0.075, 0.797, f'Not OK: {len(xs_bad):,.0f}', fontsize=9, color='#334155', va='center')
        side.text(0.0, 0.68, 'Red points show locations that do not meet the selected indicator.',
                  fontsize=8.2, color='#64748b', wrap=True)

        if xmin is not None:
            dx = xmax - xmin
            dy = ymax - ymin
            pad = max(dx, dy) * 0.04 if max(dx, dy) > 0 else 1
            ax.set_xlim(xmin - pad, xmax + pad)
            ax.set_ylim(ymin - pad, ymax + pad)

        ax.set_aspect('equal', adjustable='box')
        ax.axis('off')
        ax.set_facecolor('#eef2f7')
        ax.annotate('N', xy=(0.95, 0.18), xytext=(0.95, 0.08), xycoords='axes fraction',
                    arrowprops=dict(facecolor='#0f172a', width=3, headwidth=10),
                    ha='center', va='center', fontsize=10, fontweight='bold', color='#0f172a')

        fig.savefig(path, bbox_inches='tight', facecolor=fig.get_facecolor())
        plt.close(fig)

    def _top_rank_chart(self, plt, path, title, rows, label_key, value_key, subtitle=None, top_n=10):
        valid = []
        for r in rows:
            try:
                valid.append((float(r.get(value_key, 0)), str(r.get(label_key, r.get('fid', 'Unknown')))))
            except Exception:
                pass
        valid.sort(reverse=True)
        top = valid[:top_n]
        if not top:
            labels, values = ['No data'], [0]
        else:
            values = [v for v, l in top]
            labels = [l for v, l in top]
        self._save_bar(plt, path, title, labels, values, ylabel=value_key, subtitle=subtitle, horizontal=True)

    def _generate_pngs(self, png_folder, building_rows, block_rows, admin_rows,
                       building_map_features, block_map_features, admin_map_features, feedback):
        plt, MplPolygon, PatchCollection = self._try_import_plotting()
        if plt is None:
            feedback.pushWarning('Matplotlib is not available. PNG insights were not generated.')
            return []

        os.makedirs(png_folder, exist_ok=True)
        paths = []

        n_buildings = len(building_rows)
        n_blocks = len(block_rows)

        b_3_ok = sum(1 for r in building_rows if r.get('ok_3tree') == 1)
        b_300_ok = sum(1 for r in building_rows if r.get('ok_300m') == 1)
        bl_30_ok = sum(1 for r in block_rows if r.get('ok_30pct') == 1)
        bl_300_ok = sum(1 for r in block_rows if r.get('ok_300m') == 1)

        total_pop = sum(float(r.get('pop_total', 0)) for r in block_rows)
        pop_served = sum(float(r.get('pop_served', 0)) for r in block_rows)
        pop_unserved = sum(float(r.get('pop_unserv', 0)) for r in block_rows)
        vuln_unserved = sum(float(r.get('vuln_unserv', 0)) for r in block_rows)

        very_high_blocks = sum(1 for r in block_rows if r.get('eq_class') == 'Very High Equity Priority')

        stats = {
            'n_buildings': n_buildings,
            'pct_3tree_ok': (b_3_ok / n_buildings * 100.0) if n_buildings else 0.0,
            'n_blocks': n_blocks,
            'pct_30_ok': (bl_30_ok / n_blocks * 100.0) if n_blocks else 0.0,
            'pct_300_ok': (bl_300_ok / n_blocks * 100.0) if n_blocks else 0.0,
            'pct_pop_served': (pop_served / total_pop * 100.0) if total_pop else 0.0,
            'vuln_unserved': vuln_unserved,
            'very_high_blocks': very_high_blocks
        }

        p = os.path.join(png_folder, '01_urgreecs_scorecard_dashboard.png')
        self._save_scorecard(plt, p, stats)
        paths.append(p)

        p = os.path.join(png_folder, '02_building_3_tree_compliance.png')
        self._save_bar(plt, p, 'Building Compliance: Minimum 3 Tree Proxy',
                       ['OK', 'Not OK'], [b_3_ok, n_buildings - b_3_ok],
                       ylabel='Buildings',
                       subtitle='CHM pixels ≥ 3 m inside building buffer excluding roof/building footprint.')
        paths.append(p)

        p = os.path.join(png_folder, '03_block_30_percent_green_compliance.png')
        self._save_bar(plt, p, 'Block Compliance: 30 Percent Green Cover',
                       ['OK', 'Not OK'], [bl_30_ok, n_blocks - bl_30_ok],
                       ylabel='Blocks',
                       subtitle='Green cover is derived from CHM canopy pixels ≥ 3 m.')
        paths.append(p)

        p = os.path.join(png_folder, '04_block_300m_access_compliance.png')
        self._save_bar(plt, p, 'Block Compliance: 300 m Public Green Access',
                       ['Within 300 m', 'Beyond 300 m'], [bl_300_ok, n_blocks - bl_300_ok],
                       ylabel='Blocks',
                       subtitle='Distance is measured from block centroid to nearest public green space.')
        paths.append(p)

        p = os.path.join(png_folder, '05_population_served_unserved.png')
        self._save_bar(plt, p, 'Population Served by 300 m Green Access',
                       ['Served', 'Unserved'], [pop_served, pop_unserved],
                       ylabel='Population',
                       subtitle='Population is summed from raster cells inside each block.')
        paths.append(p)

        p = os.path.join(png_folder, '06_vulnerable_population_served_unserved.png')
        vuln_served = sum(float(r.get('vuln_served', 0)) for r in block_rows)
        self._save_bar(plt, p, 'Vulnerable Population Served and Unserved',
                       ['Served', 'Unserved'], [vuln_served, vuln_unserved],
                       ylabel='Vulnerable population',
                       subtitle='Vulnerable population combines optional baby, women, and elderly rasters.')
        paths.append(p)

        p = os.path.join(png_folder, '07_green_cover_distribution.png')
        self._save_hist(plt, p, 'Distribution of Block Green Cover',
                        [r.get('green_pct', 0) for r in block_rows],
                        'Green Cover (%)',
                        subtitle='Green cover values are capped at 100% for stable interpretation.')
        paths.append(p)

        p = os.path.join(png_folder, '08_equity_score_distribution.png')
        self._save_hist(plt, p, 'Distribution of Green Equity Priority Score',
                        [r.get('eq_score', 0) for r in block_rows],
                        'Equity Priority Score',
                        subtitle='Higher score indicates stronger combined green equity deficit.')
        paths.append(p)

        p = os.path.join(png_folder, '09_green_cover_vs_access_distance.png')
        self._save_scatter(plt, p, 'Green Cover vs Distance to Public Green Space',
                           [r.get('green_pct', 0) for r in block_rows],
                           [r.get('dist_rth', -1) for r in block_rows],
                           'Green Cover (%)', 'Distance to nearest RTH (m)',
                           subtitle='Dashed thresholds represent 30% canopy and 300 m access.')
        paths.append(p)

        class_counts = {}
        for r in block_rows:
            c = r.get('eq_class', 'Unknown')
            class_counts[c] = class_counts.get(c, 0) + 1

        p = os.path.join(png_folder, '10_green_equity_priority_class.png')
        self._save_bar(plt, p, 'Green Equity Priority Class',
                       list(class_counts.keys()), [class_counts[k] for k in class_counts.keys()],
                       ylabel='Blocks',
                       subtitle='Class combines canopy deficit, access deficit, and vulnerable exposure.')
        paths.append(p)

        p = os.path.join(png_folder, '11_top_priority_blocks.png')
        self._top_rank_chart(plt, p, 'Top Priority Blocks for Green Equity Intervention',
                             block_rows, 'fid', 'eq_score',
                             subtitle='Ranking uses green equity priority score.', top_n=15)
        paths.append(p)

        # Block maps
        if block_map_features:
            feedback.pushInfo('Generating block map PNGs with corrected keys: class_330 and pop_unserv...')
            for item in block_map_features:
                item['access_label'] = 'Within 300 m' if item.get('ok_300m') == 1 else 'Beyond 300 m'
                item['tree30_label'] = 'OK' if item.get('ok_30pct') == 1 else 'Not OK'

            p = os.path.join(png_folder, '12_map_block_green_cover_percent.png')
            self._plot_polygon_map(plt, MplPolygon, PatchCollection, p,
                                   'Map of Block Green Cover Percentage',
                                   'Canopy cover derived from CHM pixels ≥ 3 m. Display scale is fixed to 0-100%.',
                                   block_map_features, value_key='green_pct', numeric=True,
                                   legend_title='Green Cover (%)', fixed_min=0, fixed_max=100)
            paths.append(p)

            p = os.path.join(png_folder, '13_map_block_300m_access.png')
            self._plot_polygon_map(plt, MplPolygon, PatchCollection, p,
                                   'Map of 300 m Access to Public Green Space',
                                   'Blocks are classified by centroid distance to nearest RTH/public park.',
                                   block_map_features, class_key='access_label', numeric=False,
                                   legend_title='300 m Access')
            paths.append(p)

            p = os.path.join(png_folder, '14_map_integrated_330300_class.png')
            self._plot_polygon_map(plt, MplPolygon, PatchCollection, p,
                                   'Map of Integrated 3-30-300 Block Class',
                                   'Block classes combine 30% green cover and 300 m access indicators.',
                                   block_map_features, class_key='class_330', numeric=False,
                                   legend_title='3-30-300 Class')
            paths.append(p)

            p = os.path.join(png_folder, '15_map_unserved_population.png')
            self._plot_polygon_map(plt, MplPolygon, PatchCollection, p,
                                   'Map of Unserved Population',
                                   'Unserved population indicates residents outside 300 m green access.',
                                   block_map_features, value_key='pop_unserv', numeric=True,
                                   legend_title='Unserved Population')
            paths.append(p)

            p = os.path.join(png_folder, '16_map_vulnerable_unserved_population.png')
            self._plot_polygon_map(plt, MplPolygon, PatchCollection, p,
                                   'Map of Vulnerable Unserved Population',
                                   'Baby, women, and elderly population not served by 300 m green access.',
                                   block_map_features, value_key='vuln_unserv', numeric=True,
                                   legend_title='Vulnerable Unserved')
            paths.append(p)

            p = os.path.join(png_folder, '17_map_green_equity_priority_score.png')
            self._plot_polygon_map(plt, MplPolygon, PatchCollection, p,
                                   'Map of Green Equity Priority Score',
                                   'Higher values indicate stronger combined deficit and higher intervention priority.',
                                   block_map_features, value_key='eq_score', numeric=True,
                                   legend_title='Equity Score', fixed_min=0, fixed_max=100)
            paths.append(p)

            p = os.path.join(png_folder, '18_map_green_equity_priority_class.png')
            self._plot_polygon_map(plt, MplPolygon, PatchCollection, p,
                                   'Map of Green Equity Priority Class',
                                   'Priority class based on canopy deficit, access deficit, and vulnerable exposure.',
                                   block_map_features, class_key='eq_class', numeric=False,
                                   legend_title='Equity Class')
            paths.append(p)

        # Building maps
        if building_map_features:
            p = os.path.join(png_folder, '19_map_building_3_tree_compliance.png')
            self._plot_building_map(plt, MplPolygon, PatchCollection, p,
                                    'Map of Building-Level 3-Tree Proxy',
                                    'Red points identify buildings with fewer than three CHM canopy pixels in the outer buffer.',
                                    building_map_features, block_features=block_map_features,
                                    class_key='ok_3tree_label')
            paths.append(p)

            p = os.path.join(png_folder, '20_map_building_300m_access.png')
            self._plot_building_map(plt, MplPolygon, PatchCollection, p,
                                    'Map of Building-Level 300 m Access',
                                    'Red points identify buildings located beyond 300 m from public green space.',
                                    building_map_features, block_features=block_map_features,
                                    class_key='ok_300m_label')
            paths.append(p)

        # Admin outputs
        if admin_rows:
            p = os.path.join(png_folder, '21_top_priority_admin.png')
            self._top_rank_chart(plt, p, 'Top Priority Kelurahan/Admin Areas',
                                 admin_rows, 'admin_name', 'eq_score',
                                 subtitle='Administrative ranking based on aggregated green equity priority score.', top_n=15)
            paths.append(p)

        if admin_map_features:
            p = os.path.join(png_folder, '22_map_admin_green_equity_score.png')
            self._plot_polygon_map(plt, MplPolygon, PatchCollection, p,
                                   'Map of Kelurahan/Admin Green Equity Score',
                                   'Administrative aggregation of green equity priority.',
                                   admin_map_features, value_key='eq_score', numeric=True,
                                   legend_title='Admin Equity Score', fixed_min=0, fixed_max=100)
            paths.append(p)

            p = os.path.join(png_folder, '23_map_admin_green_equity_class.png')
            self._plot_polygon_map(plt, MplPolygon, PatchCollection, p,
                                   'Map of Kelurahan/Admin Green Equity Class',
                                   'Administrative priority class for green equity interventions.',
                                   admin_map_features, class_key='eq_class', numeric=False,
                                   legend_title='Admin Equity Class')
            paths.append(p)

            p = os.path.join(png_folder, '24_map_admin_vulnerable_unserved.png')
            self._plot_polygon_map(plt, MplPolygon, PatchCollection, p,
                                   'Map of Kelurahan/Admin Vulnerable Unserved Population',
                                   'Aggregated vulnerable population not served by 300 m green access.',
                                   admin_map_features, value_key='vuln_unserv', numeric=True,
                                   legend_title='Vulnerable Unserved')
            paths.append(p)

        feedback.pushInfo(f'PNG insights generated: {len(paths)} files')
        for p in paths:
            feedback.pushInfo(p)

        return paths

    # ------------------------------------------------------------------
    # Admin aggregation
    # ------------------------------------------------------------------

    def _make_admin_fields(self, admin_source):
        base_fields = admin_source.fields() if admin_source is not None else None
        if base_fields is None:
            from qgis.core import QgsFields
            base_fields = QgsFields()

        additions = [
            ('admin_name', QVariant.String),
            ('n_blocks', QVariant.Int),
            ('n_build', QVariant.Int),
            ('mean_green', QVariant.Double),
            ('pct_30_ok', QVariant.Double),
            ('pct_300_ok', QVariant.Double),
            ('pop_total', QVariant.Double),
            ('pop_vuln', QVariant.Double),
            ('vuln_unserv', QVariant.Double),
            ('vuln_unspc', QVariant.Double),
            ('mean_dist', QVariant.Double),
            ('eq_score', QVariant.Double),
            ('eq_class', QVariant.String),
            ('main_prob', QVariant.String),
            ('rec_action', QVariant.String)
        ]
        return self._clone_fields_with_additions(base_fields, additions)

    def _aggregate_admin(self, admin_source, admin_name_field, block_rows, block_map_features,
                         buildings_map_features, feedback=None):
        """
        Optimized admin aggregation using QgsSpatialIndex.

        Previous version used nested loops:
        admin x blocks + admin x buildings.
        That becomes very slow for large building/block layers.

        This version:
        1. Converts block and building centroids into lightweight point features.
        2. Builds spatial indices.
        3. For each admin polygon, only tests centroid candidates whose bounding boxes intersect the admin bbox.
        """
        if admin_source is None:
            return [], []

        if feedback:
            feedback.pushInfo('Running optimized admin aggregation with spatial index...')

        # Build block centroid features and lookup
        block_centroid_features = []
        block_lookup = {}

        for i, (row, item) in enumerate(zip(block_rows, block_map_features)):
            g = item.get('geom')
            if g is None or g.isEmpty():
                continue
            try:
                centroid = g.centroid()
                f = QgsFeature()
                f.setId(i)
                f.setGeometry(centroid)
                block_centroid_features.append(f)
                block_lookup[i] = row
            except Exception:
                continue

        block_index = QgsSpatialIndex()
        for _f in block_centroid_features:
            block_index.addFeature(_f)

        # Build building centroid features and lookup
        building_centroid_features = []
        building_lookup = {}

        for i, item in enumerate(buildings_map_features):
            g = item.get('geom')
            if g is None or g.isEmpty():
                continue
            try:
                centroid = g if g.type() == QgsWkbTypes.PointGeometry else g.centroid()
                f = QgsFeature()
                f.setId(i)
                f.setGeometry(centroid)
                building_centroid_features.append(f)
                building_lookup[i] = item
            except Exception:
                continue

        building_index = QgsSpatialIndex()
        for _f in building_centroid_features:
            building_index.addFeature(_f)

        block_geom_by_id = {f.id(): f.geometry() for f in block_centroid_features}
        building_geom_by_id = {f.id(): f.geometry() for f in building_centroid_features}

        if feedback:
            feedback.pushInfo(f'Spatial index ready: {len(block_lookup)} block centroids and {len(building_lookup)} building centroids.')

        admin_rows = []
        admin_map_features = []

        admin_features = list(admin_source.getFeatures())
        total_admin = len(admin_features)

        admin_field_names = [f.name() for f in admin_source.fields()]

        for idx_admin, af in enumerate(admin_features):
            if feedback and feedback.isCanceled():
                break

            ag = af.geometry()
            ag = self._safe_make_valid(ag)
            if ag is None or ag.isEmpty():
                continue

            if admin_name_field and admin_name_field in admin_field_names:
                try:
                    name = str(af[admin_name_field])
                except Exception:
                    name = str(af.id())
            else:
                name = str(af.id())

            # Candidate block centroids from spatial index
            assigned_blocks = []
            try:
                candidate_block_ids = block_index.intersects(ag.boundingBox())
            except Exception:
                candidate_block_ids = []

            for bid in candidate_block_ids:
                bg = block_geom_by_id.get(bid)
                if bg is None:
                    continue
                try:
                    if ag.contains(bg):
                        row = block_lookup.get(bid)
                        if row is not None:
                            assigned_blocks.append(row)
                except Exception:
                    pass

            # Candidate building centroids from spatial index
            assigned_builds = 0
            try:
                candidate_building_ids = building_index.intersects(ag.boundingBox())
            except Exception:
                candidate_building_ids = []

            for gid in candidate_building_ids:
                gg = building_geom_by_id.get(gid)
                if gg is None:
                    continue
                try:
                    if ag.contains(gg):
                        assigned_builds += 1
                except Exception:
                    pass

            n_blocks = len(assigned_blocks)
            pop_total = sum(float(r.get('pop_total', 0)) for r in assigned_blocks)
            pop_vuln = sum(float(r.get('pop_vuln', 0)) for r in assigned_blocks)
            vuln_unserv = sum(float(r.get('vuln_unserv', 0)) for r in assigned_blocks)
            mean_green = (sum(float(r.get('green_pct', 0)) for r in assigned_blocks) / n_blocks) if n_blocks else 0.0
            pct_30_ok = (sum(int(r.get('ok_30pct', 0)) for r in assigned_blocks) / n_blocks * 100.0) if n_blocks else 0.0
            pct_300_ok = (sum(int(r.get('ok_300m', 0)) for r in assigned_blocks) / n_blocks * 100.0) if n_blocks else 0.0

            dists = [float(r.get('dist_rth', -1)) for r in assigned_blocks if float(r.get('dist_rth', -1)) >= 0]
            mean_dist = (sum(dists) / len(dists)) if dists else -1.0

            vuln_unspc = (vuln_unserv / pop_vuln * 100.0) if pop_vuln > 0 else 0.0

            canopy_def = max(0.0, 30.0 - mean_green) / 30.0
            canopy_def = max(0.0, min(canopy_def, 1.0))
            access_def = max(0.0, 100.0 - pct_300_ok) / 100.0
            vuln_exposure = max(0.0, min(vuln_unspc / 100.0, 1.0))

            eq_score = (0.35 * canopy_def + 0.30 * access_def + 0.35 * vuln_exposure) * 100.0
            eq_class = self._equity_class(eq_score)
            main_prob, rec_action = self._main_problem_and_action(canopy_def, access_def, vuln_exposure)

            row = {
                'fid': af.id(),
                'admin_name': name,
                'n_blocks': n_blocks,
                'n_build': assigned_builds,
                'mean_green': mean_green,
                'pct_30_ok': pct_30_ok,
                'pct_300_ok': pct_300_ok,
                'pop_total': pop_total,
                'pop_vuln': pop_vuln,
                'vuln_unserv': vuln_unserv,
                'vuln_unspc': vuln_unspc,
                'mean_dist': mean_dist,
                'eq_score': eq_score,
                'eq_class': eq_class,
                'main_prob': main_prob,
                'rec_action': rec_action
            }
            admin_rows.append(row)

            map_item = dict(row)
            map_item['geom'] = QgsGeometry(ag)
            admin_map_features.append(map_item)

            if feedback and total_admin > 0:
                feedback.setProgressText(f'Admin aggregation: {idx_admin + 1}/{total_admin}')

        if feedback:
            feedback.pushInfo(f'Admin aggregation completed: {len(admin_rows)} admin features.')

        return admin_rows, admin_map_features

    # ------------------------------------------------------------------
    # Main process
    # ------------------------------------------------------------------

    def processAlgorithm(self, parameters, context, feedback):

        buildings = self.parameterAsSource(parameters, self.BUILDINGS, context)
        blocks = self.parameterAsSource(parameters, self.BLOCKS, context)
        chm_layer = self.parameterAsRasterLayer(parameters, self.CHM, context)
        pop_total_raster = self.parameterAsRasterLayer(parameters, self.POP_TOTAL, context)
        pop_baby_raster = self.parameterAsRasterLayer(parameters, self.POP_BABY, context)
        pop_women_raster = self.parameterAsRasterLayer(parameters, self.POP_WOMEN, context)
        pop_elderly_raster = self.parameterAsRasterLayer(parameters, self.POP_ELDERLY, context)
        rth = self.parameterAsSource(parameters, self.RTH, context)
        admin = self.parameterAsSource(parameters, self.ADMIN, context)

        admin_name_field = self.parameterAsString(parameters, self.ADMIN_NAME_FIELD, context)
        buffer_dist = self.parameterAsDouble(parameters, self.BUFFER, context)
        out_block_csv = self.parameterAsFileOutput(parameters, self.OUT_BLOCK_CSV, context)
        out_admin_csv = self.parameterAsFileOutput(parameters, self.OUT_ADMIN_CSV, context)
        png_folder = self.parameterAsString(parameters, self.OUT_PNG_FOLDER, context)

        if buildings is None:
            raise QgsProcessingException('Building layer is invalid.')
        if blocks is None:
            raise QgsProcessingException('Urban block layer is invalid.')
        if chm_layer is None:
            raise QgsProcessingException('CHM raster is invalid.')
        if pop_total_raster is None:
            raise QgsProcessingException('Total population raster is invalid.')
        if rth is None:
            raise QgsProcessingException('RTH/public green space layer is invalid.')

        self._ensure_metric_crs(buildings, 'Building layer')
        self._ensure_metric_crs(blocks, 'Urban block layer')
        self._ensure_metric_crs(rth, 'RTH layer')
        if admin is not None:
            self._ensure_metric_crs(admin, 'Admin boundary layer')

        os.makedirs(os.path.dirname(out_block_csv), exist_ok=True) if os.path.dirname(out_block_csv) else None
        os.makedirs(os.path.dirname(out_admin_csv), exist_ok=True) if os.path.dirname(out_admin_csv) else None
        os.makedirs(png_folder, exist_ok=True)

        rth_geoms = self._collect_rth_points(rth)
        if not rth_geoms:
            raise QgsProcessingException('No valid RTH/public green space geometry found.')

        # ------------------------------------------------------------------
        # Prepare output fields
        # ------------------------------------------------------------------

        building_fields = self._clone_fields_with_additions(
            buildings.fields(),
            [
                ('tree_px30', QVariant.Int),
                ('ok_3tree', QVariant.Int),
                ('dist_rth', QVariant.Double),
                ('ok_300m', QVariant.Int)
            ]
        )

        block_fields = self._clone_fields_with_additions(
            blocks.fields(),
            [
                ('area_blk', QVariant.Double),
                ('canopy_m2', QVariant.Double),
                ('green_pct', QVariant.Double),
                ('ok_30pct', QVariant.Int),
                ('pop_total', QVariant.Double),
                ('pop_baby', QVariant.Double),
                ('pop_women', QVariant.Double),
                ('pop_elder', QVariant.Double),
                ('pop_vuln', QVariant.Double),
                ('dist_rth', QVariant.Double),
                ('ok_300m', QVariant.Int),
                ('pop_served', QVariant.Double),
                ('pop_unserv', QVariant.Double),
                ('vuln_served', QVariant.Double),
                ('vuln_unserv', QVariant.Double),
                ('vuln_unspc', QVariant.Double),
                ('score_330', QVariant.Int),
                ('class_330', QVariant.String),
                ('eq_score', QVariant.Double),
                ('eq_class', QVariant.String),
                ('main_prob', QVariant.String),
                ('rec_action', QVariant.String)
            ]
        )

        admin_fields = self._make_admin_fields(admin)

        sink_buildings, dest_buildings = self.parameterAsSink(
            parameters, self.OUT_BUILDINGS, context,
            building_fields, buildings.wkbType(), buildings.sourceCrs()
        )
        if sink_buildings is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUT_BUILDINGS))

        sink_blocks, dest_blocks = self.parameterAsSink(
            parameters, self.OUT_BLOCKS, context,
            block_fields, blocks.wkbType(), blocks.sourceCrs()
        )
        if sink_blocks is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUT_BLOCKS))

        admin_wkb = admin.wkbType() if admin is not None else QgsWkbTypes.Polygon
        admin_crs = admin.sourceCrs() if admin is not None else blocks.sourceCrs()
        sink_admin, dest_admin = self.parameterAsSink(
            parameters, self.OUT_ADMIN, context,
            admin_fields, admin_wkb, admin_crs
        )
        if sink_admin is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUT_ADMIN))

        # ------------------------------------------------------------------
        # Building analysis
        # ------------------------------------------------------------------

        feedback.pushInfo('Running building-level 3-tree and 300 m access analysis...')

        building_rows = []
        building_map_features = []

        idx_tree_px = building_fields.indexFromName('tree_px30')
        idx_ok_3tree = building_fields.indexFromName('ok_3tree')
        idx_dist_b = building_fields.indexFromName('dist_rth')
        idx_ok_300_b = building_fields.indexFromName('ok_300m')

        n_buildings = buildings.featureCount()
        n_blocks = blocks.featureCount()
        total_steps = max(1, n_buildings + n_blocks)
        processed = 0

        for feat in buildings.getFeatures():

            if feedback.isCanceled():
                break

            geom = self._safe_make_valid(feat.geometry())

            if geom is None or geom.isEmpty():
                tree_count = 0
                dist_rth = -1.0
            else:
                if geom.type() == QgsWkbTypes.PointGeometry:
                    outer_buffer = geom.buffer(buffer_dist, 24)
                    dist_geom = geom
                else:
                    buffer_geom = self._safe_make_valid(geom.buffer(buffer_dist, 24))
                    outer_buffer = self._safe_make_valid(buffer_geom.difference(geom))
                    dist_geom = geom.centroid()

                tree_count, _ = self._count_raster_pixels_ge(
                    chm_layer, outer_buffer, buildings.sourceCrs(), 3.0, context
                )

                dist_rth = self._nearest_distance(dist_geom, rth_geoms)

            ok_3tree = 1 if tree_count >= 3 else 0
            ok_300m = 1 if dist_rth >= 0 and dist_rth <= 300 else 0

            out_feat = QgsFeature(building_fields)
            out_feat.setGeometry(feat.geometry())
            self._copy_original_attrs(out_feat, feat)
            out_feat.setAttribute(idx_tree_px, int(tree_count))
            out_feat.setAttribute(idx_ok_3tree, int(ok_3tree))
            out_feat.setAttribute(idx_dist_b, float(dist_rth))
            out_feat.setAttribute(idx_ok_300_b, int(ok_300m))
            sink_buildings.addFeature(out_feat, QgsFeatureSink.FastInsert)

            row = {
                'fid': feat.id(),
                'tree_px30': int(tree_count),
                'ok_3tree': int(ok_3tree),
                'dist_rth': float(dist_rth),
                'ok_300m': int(ok_300m)
            }
            building_rows.append(row)

            building_map_features.append({
                'fid': feat.id(),
                'geom': QgsGeometry(feat.geometry()),
                'tree_px30': int(tree_count),
                'ok_3tree': int(ok_3tree),
                'ok_3tree_label': 'OK' if ok_3tree == 1 else 'Not OK',
                'dist_rth': float(dist_rth),
                'ok_300m': int(ok_300m),
                'ok_300m_label': 'OK' if ok_300m == 1 else 'Not OK'
            })

            processed += 1
            feedback.setProgress(int(processed / total_steps * 100))

        # ------------------------------------------------------------------
        # First block pass to calculate physical and population indicators
        # ------------------------------------------------------------------

        feedback.pushInfo('Running block-level canopy, population, access, and green equity analysis...')

        block_pre_rows = []
        max_vuln_unserved = 0.0

        for feat in blocks.getFeatures():

            if feedback.isCanceled():
                break

            geom = self._safe_make_valid(feat.geometry())

            if geom is None or geom.isEmpty():
                area_blk = 0.0
                canopy_m2 = 0.0
                green_pct = 0.0
                pop_total = pop_baby = pop_women = pop_elder = 0.0
                dist_rth = -1.0
            else:
                area_blk = float(geom.area())

                canopy_count, px_area = self._count_raster_pixels_ge(
                    chm_layer, geom, blocks.sourceCrs(), 3.0, context
                )

                canopy_m2_raw = float(canopy_count) * float(px_area)
                canopy_m2 = min(canopy_m2_raw, area_blk) if area_blk > 0 else 0.0
                green_pct = (canopy_m2 / area_blk * 100.0) if area_blk > 0 else 0.0
                green_pct = max(0.0, min(green_pct, 100.0))

                pop_total = self._sum_raster_inside_geom(pop_total_raster, geom, blocks.sourceCrs(), context)
                pop_baby = self._sum_raster_inside_geom(pop_baby_raster, geom, blocks.sourceCrs(), context) if pop_baby_raster else 0.0
                pop_women = self._sum_raster_inside_geom(pop_women_raster, geom, blocks.sourceCrs(), context) if pop_women_raster else 0.0
                pop_elder = self._sum_raster_inside_geom(pop_elderly_raster, geom, blocks.sourceCrs(), context) if pop_elderly_raster else 0.0

                dist_rth = self._nearest_distance(geom.centroid(), rth_geoms)

            pop_vuln = pop_baby + pop_women + pop_elder

            ok_30pct = 1 if green_pct >= 30.0 else 0
            ok_300m = 1 if dist_rth >= 0 and dist_rth <= 300.0 else 0

            pop_served = pop_total if ok_300m == 1 else 0.0
            pop_unserv = pop_total if ok_300m == 0 else 0.0
            vuln_served = pop_vuln if ok_300m == 1 else 0.0
            vuln_unserv = pop_vuln if ok_300m == 0 else 0.0
            vuln_unspc = (vuln_unserv / pop_vuln * 100.0) if pop_vuln > 0 else 0.0

            if vuln_unserv > max_vuln_unserved:
                max_vuln_unserved = vuln_unserv

            score_330 = int(ok_30pct) + int(ok_300m)
            class_330 = self._class_330300(ok_30pct, ok_300m)

            block_pre_rows.append({
                'feature': feat,
                'geom': QgsGeometry(feat.geometry()),
                'area_blk': float(area_blk),
                'canopy_m2': float(canopy_m2),
                'green_pct': float(green_pct),
                'ok_30pct': int(ok_30pct),
                'pop_total': float(pop_total),
                'pop_baby': float(pop_baby),
                'pop_women': float(pop_women),
                'pop_elder': float(pop_elder),
                'pop_vuln': float(pop_vuln),
                'dist_rth': float(dist_rth),
                'ok_300m': int(ok_300m),
                'pop_served': float(pop_served),
                'pop_unserv': float(pop_unserv),
                'vuln_served': float(vuln_served),
                'vuln_unserv': float(vuln_unserv),
                'vuln_unspc': float(vuln_unspc),
                'score_330': int(score_330),
                'class_330': class_330,
                # Backward-compatible aliases for PNG functions / older versions
                'pop_unserved': float(pop_unserv),
                'class_330300': class_330
            })

        # ------------------------------------------------------------------
        # Second block pass to calculate equity score and write output
        # ------------------------------------------------------------------

        block_rows = []
        block_map_features = []
        block_csv_rows = []

        idx = {name: block_fields.indexFromName(name) for name in [
            'area_blk', 'canopy_m2', 'green_pct', 'ok_30pct',
            'pop_total', 'pop_baby', 'pop_women', 'pop_elder', 'pop_vuln',
            'dist_rth', 'ok_300m', 'pop_served', 'pop_unserv',
            'vuln_served', 'vuln_unserv', 'vuln_unspc',
            'score_330', 'class_330', 'eq_score', 'eq_class',
            'main_prob', 'rec_action'
        ]}

        for item in block_pre_rows:

            feat = item['feature']

            eq_score, canopy_def, access_def, vuln_exposure = self._compute_equity_score(
                item['green_pct'], item['dist_rth'], item['vuln_unserv'], max_vuln_unserved
            )
            eq_class = self._equity_class(eq_score)
            main_prob, rec_action = self._main_problem_and_action(canopy_def, access_def, vuln_exposure)

            out_feat = QgsFeature(block_fields)
            out_feat.setGeometry(feat.geometry())
            self._copy_original_attrs(out_feat, feat)

            for key in [
                'area_blk', 'canopy_m2', 'green_pct', 'ok_30pct',
                'pop_total', 'pop_baby', 'pop_women', 'pop_elder', 'pop_vuln',
                'dist_rth', 'ok_300m', 'pop_served', 'pop_unserv',
                'vuln_served', 'vuln_unserv', 'vuln_unspc',
                'score_330', 'class_330'
            ]:
                out_feat.setAttribute(idx[key], item[key])

            out_feat.setAttribute(idx['eq_score'], float(eq_score))
            out_feat.setAttribute(idx['eq_class'], eq_class)
            out_feat.setAttribute(idx['main_prob'], main_prob)
            out_feat.setAttribute(idx['rec_action'], rec_action)

            sink_blocks.addFeature(out_feat, QgsFeatureSink.FastInsert)
            block_csv_rows.append(out_feat.attributes())

            row = {
                'fid': feat.id(),
                **{k: item[k] for k in item.keys() if k not in ['feature', 'geom']},
                'eq_score': float(eq_score),
                'eq_class': eq_class,
                'main_prob': main_prob,
                'rec_action': rec_action,
                # Backward-compatible aliases for PNG functions / older versions
                'pop_unserved': float(item.get('pop_unserv', 0)),
                'class_330300': item.get('class_330', 'Unknown')
            }
            block_rows.append(row)

            map_item = dict(row)
            map_item['geom'] = QgsGeometry(feat.geometry())
            block_map_features.append(map_item)

            processed += 1
            feedback.setProgress(int(processed / total_steps * 100))

        # ------------------------------------------------------------------
        # Write block CSV
        # ------------------------------------------------------------------

        with open(out_block_csv, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([f.name() for f in block_fields])
            writer.writerows(block_csv_rows)

        feedback.pushInfo(f'Block CSV saved: {out_block_csv}')

        # ------------------------------------------------------------------
        # Admin aggregation and output
        # ------------------------------------------------------------------

        feedback.pushInfo('Block processing completed. Next step: admin aggregation and PNG generation.')

        feedback.pushInfo('Starting admin aggregation after block CSV...')
        admin_rows, admin_map_features = self._aggregate_admin(
            admin, admin_name_field, block_rows, block_map_features, building_map_features, feedback=feedback
        )

        admin_csv_rows = []

        admin_field_idx = {f.name(): admin_fields.indexFromName(f.name()) for f in admin_fields}

        if admin is not None:
            # Map admin feature by id for writing geometries with original attributes
            admin_feature_by_id = {f.id(): f for f in admin.getFeatures()}

            for row in admin_rows:
                af = admin_feature_by_id.get(row['fid'])
                if af is None:
                    continue

                out_admin_feat = QgsFeature(admin_fields)
                out_admin_feat.setGeometry(af.geometry())
                self._copy_original_attrs(out_admin_feat, af)

                for key, value in row.items():
                    if key in admin_field_idx:
                        out_admin_feat.setAttribute(admin_field_idx[key], value)

                sink_admin.addFeature(out_admin_feat, QgsFeatureSink.FastInsert)
                admin_csv_rows.append(out_admin_feat.attributes())

        with open(out_admin_csv, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([f.name() for f in admin_fields])
            writer.writerows(admin_csv_rows)

        feedback.pushInfo(f'Admin CSV saved: {out_admin_csv}')

        # ------------------------------------------------------------------
        # PNG insights
        # ------------------------------------------------------------------

        feedback.pushInfo('Generating URGREECS PNG insights. This can take time for large polygon/building layers...')
        self._generate_pngs(
            png_folder,
            building_rows,
            block_rows,
            admin_rows,
            building_map_features,
            block_map_features,
            admin_map_features,
            feedback
        )

        feedback.pushInfo('URGREECS Urban Green Equity Analytics 3-30-300 completed.')

        return {
            self.OUT_BUILDINGS: dest_buildings,
            self.OUT_BLOCKS: dest_blocks,
            self.OUT_ADMIN: dest_admin,
            self.OUT_BLOCK_CSV: out_block_csv,
            self.OUT_ADMIN_CSV: out_admin_csv,
            self.OUT_PNG_FOLDER: png_folder
        }
