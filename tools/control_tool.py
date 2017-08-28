# -*- coding: utf-8 -*-
"""
/***************************************************************************
 VDLTools
                                 A QGIS plugin for the Ville de Lausanne
                              -------------------
        begin                : 2017-02-14
        git sha              : $Format:%H$
        copyright            : (C) 2016 Ville de Lausanne
        author               : Christophe Gusthiot
        email                : christophe.gusthiot@lausanne.ch
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from __future__ import division
from PyQt4.QtCore import QCoreApplication
from PyQt4.QtGui import QProgressBar,QMessageBox
from .area_tool import AreaTool
from ..ui.choose_control_dialog import ChooseControlDialog
from qgis.gui import (QgsMessageBar,
                      QgsLegendInterface)
from qgis.core import (QgsMapLayerRegistry,
                       QgsVectorLayer,
                       QgsGeometry,
                       QgsFeature,
                       QgsDataSourceURI,
                       QgsFeatureRequest,
                       QgsProject,
                       QGis,
                       QgsWKBTypes)
from ..core.db_connector import DBConnector
from datetime import datetime


class ControlTool(AreaTool):
    """
    Map tool class to make control request
    """

    def __init__(self, iface):
        """
        Constructor
        :param iface: interface
        """
        AreaTool.__init__(self, iface)
        self.__iface = iface
        self.icon_path = ':/plugins/VDLTools/icons/control_icon.png'
        self.text = QCoreApplication.translate("VDLTools", "Make control requests on selected area")
        self.releasedSignal.connect(self.__released)
        self.__chooseDlg = None
        self.__db = None
        self.ownSettings = None
        self.__requests = {
            "nom1": self.__request1
        }
        self.__crs = None
        self.__registry = QgsMapLayerRegistry.instance() # définition du registre des couches dans le projet
        self.tableConfig = 'usr_control_request' # nom de la table/couche dans le projet qui liste tous les contrôles possible
        self.__lrequests = [] # liste des requêtes actives
        self.areaMax = 1000000 # tolérance de surface max. pour lancer un contrôle

    def toolName(self):
        """
        To get the tool name
        :return: tool name
        """
        return QCoreApplication.translate("VDLTools", "Control")

    def setTool(self):
        """
        To set the current tool as this one
        """
        self.canvas().setMapTool(self)

    def __released(self):
        """
        When selection is complete
        """
        if self.ownSettings is None:
            self.__iface.messageBar().pushMessage(QCoreApplication.translate("VDLTools", "No settings given !!"),
                                                  level=QgsMessageBar.CRITICAL, duration=0)
            return
        if self.ownSettings.ctlDb is None:
            self.__iface.messageBar().pushMessage(QCoreApplication.translate("VDLTools", "No control db given !!"),
                                                  level=QgsMessageBar.CRITICAL, duration=0)
            return
        """
        Test si la couche / table qui contient l'ensemble des contrôles existe bien dans le projet
        """

        global layerCfgControl
        try:
            layerCfgControl = (l for l in self.__registry.mapLayers().values() if QgsDataSourceURI(l.source()).table() == self.tableConfig and hasattr(l, 'providerType') and l.providerType() == 'postgres').next()
        except StopIteration:
            textConfigLayer = u"La couche qui définit la liste des contrôles possible a mal été définie ou n'existe pas dans le projet, veuilliez l'ajouter au projet"
            self.__iface.messageBar().pushMessage(textConfigLayer, level=QgsMessageBar.CRITICAL, duration=5)
            layerCfgControl = None

        """
        Test si la zone de contrôle a bien été définie par l'utilisateur
        """

        if self.geom is None:
             self.__iface.messageBar().pushMessage(u"zone de requête non définie, Veuillez définir une zone de contrôle (maintenir le clic de la souris)", level=QgsMessageBar.CRITICAL, duration=5)
        else:
            print self.geom.area()
            if self.geom.area() > self.areaMax:
                self.__iface.messageBar().pushMessage(u"Veuillez définir une zone de contrôle plus petite , max. = 1 km2", level=QgsMessageBar.CRITICAL, duration=5)

                """
                Question à l'utilisateur s'il veut continuer ou pas par rapport à une zone de contrôle hors tolérance
                """
                """
                qstBox = QMessageBox()
                qstText = u"Voulez-vous quand même continuer ??, le traitement peut prendre plusieurs minutes, voire plusieurs heures "
                qstBox.setText(qstText)
                qstBox.setWindowTitle(u"Zone de contrôle trop grande")
                qstBox.setIcon(QMessageBox.Question)
                qstBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
                repArea = qstBox.exec_()
                # print qstBox.clickedButton().text() # retourne le texte du bouton cliqué
                #bb = qstBox.clickedButton() # role du bouton cliqué (objet)
                repMaxArea = qstBox.buttonRole(qstBox.clickedButton())
                if repMaxArea == 0:
                    print u"on continue malgré tout le traitement"
                elif repMaxArea == 1:
                    print u"on arrête le traitement"
                #print repArea # réponse donnée par la touche cliqué sur la boite de dialogue
                """
            else:
                """
                Liste des contrôles actifs existants
                """
                req = QgsFeatureRequest().setFilterExpression('"active" is true')
                for f in layerCfgControl.getFeatures(req):
                    #layer_name = f[u"layer_name"]
                    #self.__lrequests[str(f[u"id"])] = f[u"layer_name"]
                    lrequests = {}
                    lrequests["id"]=str(f[u"id"])
                    lrequests["name"]=f[u"layer_name"]
                    lrequests["code"]=f[u"code_error"]
                    lrequests["check"]=f[u"check_defaut"]
                    #self.__lrequests.append(str(f[u"id"]))
                    self.__lrequests.append(lrequests)
                # trier la liste de dictionnaire
                self.__lrequests = sorted( self.__lrequests,key=lambda k: int(k['id']))
                print self.__lrequests

                #self.__chooseDlg = ChooseControlDialog(self.__requests.keys())
                self.__chooseDlg = ChooseControlDialog(self.__lrequests)
                self.__chooseDlg.okButton().clicked.connect(self.__onOk)
                self.__chooseDlg.cancelButton().clicked.connect(self.__onCancel)
                self.__chooseDlg.show()

    def __onCancel(self):
        """
        When the Cancel button in Choose Control Dialog is pushed
        """
        self.__chooseDlg.reject()
        self.geom = None # supprimer la géométrie définie
        self.__lrequests = [] # vider la liste des requêtes actives

    def __onOk(self):
        """
        When the Ok button in Choose Control Dialog is pushed
        """
        self.__chooseDlg.accept()

        self.__connector = DBConnector(self.ownSettings.ctlDb, self.__iface)
        self.__db = self.__connector.setConnection()

        if self.__db is not None and self.geom.area() > 0:
            self.__createCtrlLayers(self.__chooseDlg.controls())
            self.__cancel()

    def __createCtrlLayers(self,requete):
        """
        Création des couches de contrôles
        - selon une requête SQL dans la base de données (choix  ou des contrôle par l'utilisateur)
        - selon une zone géographique définie par l'utilisateur
        :param requete: liste des requêtes
        :return:
        """

        # récupérer la géométrie définie par l'utilisateur pour l'utiliser dans les requêtes SQL , conversion en géométrie binaire et dans le bon système de coordonnée)
        self.__crs = self.__iface.mapCanvas().mapSettings().destinationCrs().postgisSrid() # défintion du système de coordonnées en sortie (par défaut 21781), récupérer des paramètres du projets
        bbox = "(SELECT ST_GeomFromText('" + self.geom.exportToWkt() + "'," + str(self.__crs) + "))"

        # paramètres de la source des couches à ajouter au projet
        uri = QgsDataSourceURI()
        uri.setConnection(self.__db.hostName(),str(self.__db.port()), self.__db.databaseName(),self.__db.userName(),self.__db.password())
        uri.setSrid(str(self.__crs))
        outputLayers = [] # listes des couches de résultats à charger dans le projet
        for name in requete:
            #self.__requests[name]()
            for q in layerCfgControl.getFeatures(QgsFeatureRequest(int(name))):
                query_fct = q[u"sql_function"]
                query_fct = query_fct.replace("bbox",bbox)
                query = "(SELECT * FROM "+ query_fct + ")"
                if q[u"geom_type"] == "POINTZ":
                    #uri.setWkbType(QGis.WKBPoint25D)
                    uri.setWkbType(QgsWKBTypes.PointZ)
                if q[u"geom_type"] == "LINESTRINGZ":
                    #uri.setWkbType(QGis.WKBLineString25D)
                    uri.setWkbType(QgsWKBTypes.LineStringZ)
                uri.setDataSource('',query,q[u"geom_name"],"",q[u"key_attribute"])
                layer = QgsVectorLayer(uri.uri(),q[u"layer_name"], "postgres")
                print(layer.name())
                print(layer.featureCount())
                if layer.featureCount() > 0:
                    outputLayers.append(layer)
        if outputLayers is not None:
            self.__addCtrlLayers(outputLayers)

    def __addCtrlLayers(self, layers):
        totalError = 0 # décompte des erreurs détectées (nombre d'objets dans chaque couche)
        for i in range(0,len(layers)):
            totalError = totalError + layers[i].featureCount()
        print "Erreur totale : " + str(totalError)

    def __request1(self):
        """
        Request which can be choosed for control
        """
        self.__crs = self.canvas().mapSettings().destinationCrs().postgisSrid()
        layer_name = "request1"
        fNames = ["id", "fk_status"]
        select_part = """SELECT GeometryType(geometry3d), ST_AsText(geometry3d)"""
        for f in fNames:
            select_part += """, %s, pg_typeof(%s)""" % (f, f)
        from_part = """ FROM qwat_od.pipe """
        where_part = """WHERE ST_Intersects(geometry3d,ST_GeomFromText('%s',%s))""" \
                     % (self.geom.exportToWkt(), str(self.__crs))
        request = select_part + from_part + where_part
        print(request)
        self.__querying(request, layer_name, fNames)

    def __querying(self, request, layer_name, fNames):
        """
        Process query to database and display the results
        :param request: request string to query
        :param layer_name: name for new memory layer to display the results
        :param fNames: fields names requested as result
        """
        query = self.__db.exec_(request)
        if query.lastError().isValid():
            self.__iface.messageBar().pushMessage(query.lastError().text(), level=QgsMessageBar.CRITICAL, duration=0)
        else:
            gtype = None
            geometries = []
            attributes = []
            fTypes = []
            while query.next():
                gtype = query.value(0)
                geometries.append(query.value(1))
                atts = []
                for i in range(len(fNames)):
                    atts.append(query.value(2*i+2))
                    fTypes.append(query.value(2*i+3))
                attributes.append(atts)
            print(len(geometries))
            if len(geometries) > 0:
                self.__createMemoryLayer(layer_name, gtype, geometries, attributes, fNames, fTypes)

    def __createMemoryLayer(self, layer_name, gtype, geometries, attributes, fNames, fTypes):
        """
        Create a memory layer from parameters
        :param layer_name: name for the layer
        :param gtype: geometry type of the layer
        :param geometries: objects geometries
        :param attributes: objects attributes
        :param fNames: fields names
        :param fTypes: fields types
        """
        layerList = QgsMapLayerRegistry.instance().mapLayersByName(layer_name)
        if layerList:
            QgsMapLayerRegistry.instance().removeMapLayers([layerList[0].id()])
        epsg = self.canvas().mapRenderer().destinationCrs().authid()
        fieldsParam = ""
        for i in range(len(fNames)):
            fieldsParam += "&field=" + fNames[i] + ":" + fTypes[i]
        layer = QgsVectorLayer(gtype + "?crs=" + epsg + fieldsParam + "&index=yes", layer_name, "memory")
        QgsMapLayerRegistry.instance().addMapLayer(layer)
        layer.startEditing()
        for i in range(len(geometries)):
            feature = QgsFeature()
            feature.setGeometry(QgsGeometry().fromWkt(geometries[i]))
            fields = layer.pendingFields()
            feature.setFields(fields)
            for j in range(len(fNames)):
                feature.setAttribute(fNames[j], attributes[i][j])
            layer.addFeature(feature)
        layer.commitChanges()

    def __cancel(self):
        """
        To cancel used variables
        """
        self.__chooseDlg = None
        self.__db.close()
        self.geom = None # supprimer la géométrie définie
        self.__lrequests = [] # vider la liste des requêtes actives
