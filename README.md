# **IfcLCA-Py**

**IfcLCA-Py** is a Python package **— currently under development —** designed to perform Life Cycle Assessment (LCA) analysis using Industry Foundation Classes (Ifc) data. It serves as a toolkit for evaluating the impact of embodied emissions in construction projects, providing low-level logic for in-depth analysis.

![General Idea](assets/concept-overview.png)

## Possible Features

- **IFC Data Reading**: Load and interpret Ifc files, extracting detailed information about building elements and their associated materials.
- **IFC 5d**: Get the relevant quantities per element to be analyzed, such as GrossVolume etc.
- **Material Database Integration**: Connect with an environmental impact database to fetch material properties, such as carbon footprint and density.
- **LCA Analysis**: Calculate embodied emissions based on Ifc data, quantites and environmental impact data.
- **Optioneering Support**: Explore multiple options or configurations to identify possible solutions.
- **Reporting**: Generate reports detailing the environmental impacts & save results in Ifc.

## License

This project is licensed under the **GNU Affero General Public License (AGPL)**. For more information, please see the [LICENSE](LICENSE) file.
