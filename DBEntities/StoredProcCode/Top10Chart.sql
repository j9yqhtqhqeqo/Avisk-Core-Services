SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- Create the stored procedure in the specified schema
CREATE PROCEDURE[dbo].[sp_load_top10_exposure_data]


@company_name VARCHAR(100),
@SectorID INTEGER,
@Year INTEGER
AS
BEGIN

   create table  # Chart1(
       unique_key int IDENTITY,
        top10_sector_exposure varchar(100),
        degree_of_control_sector FLOAT,
        degree_of_control_company FLOAT,
        degree_of_control_sector_normalized FLOAT,
        degree_of_control_company_normalized FLOAT,
        top10_company_exposure  varchar(100),
    )

        create table  # Sector_Exposure(
        sector_exposure varchar(100),
        degree_of_control_sector FLOAT,
    )

        create table  # Company_Exposure(
        company_Exposure varchar(100),
        degree_of_control_company FLOAT,
    )

    create table  # Company_Top10(
    unique_key int IDENTITY,
    top10_company_exposure varchar(100),
    degree_of_control_company FLOAT,
    )

        TRUNCATE TABLE  # Chart1
        insert into  # Chart1
    select  top 10 exposure_path_name, NULL, NULL,NULL,NULL,NULL
    from t_sector_exp_insights where year = @Year and sector_id = @SectorID order by score_normalized DESC

        - - Degree of Control(Sector Level - Exposure vs. Mitigation)
        insert into  # Sector_Exposure
        select  exposure_path_name, avg(score) from t_sector_exp_mitigation_insights sem where
        sector_id = @SectorID and year = @Year
        group by exposure_path_name

    - - select 'Before Update Sector', * from  # Sector_Exposure
        update  # Chart1
        set  # Chart1.degree_of_control_sector = SE.degree_of_control_sector
        From
    # Chart1 C1
        INNER JOIN  # Sector_Exposure SE ON C1.top10_sector_exposure = SE.sector_exposure

        - - Degree of Control(Sector Level - Exposure vs. Company Level Mitigation)
        insert into  # Company_Exposure
        select exp.exposure_path_name, avg(score)
        from t_mitigation_exp_insights insights
        inner join t_exposure_pathway exp on exp.exposure_path_id = insights.exposure_path_id
        INNER join t_document doc on doc.document_id = insights.document_id and doc.company_name = @company_name
        where insights.year = @Year
        group by exp.exposure_path_name

        update  # Chart1
        set  # Chart1.degree_of_control_company = CE.degree_of_control_company
        From
         # Chart1 C1
        INNER JOIN  # Company_Exposure CE ON C1.top10_sector_exposure = CE.company_Exposure

        - - --Top 10 Exposure Pathways(Company Level)
        Insert into  # Company_Top10
        select top 10 exp.exposure_path_name, avg(insights.score) sc
        from t_exposure_pathway_insights insights
    inner join t_exposure_pathway exp on exp.exposure_path_id = insights.exposure_path_id
    INNER join t_document doc on doc.document_id = insights.document_id and doc.company_name = @company_name
        where
    insights.year = @Year
        GROUP by exp.exposure_path_name
        order by sc desc

        update  # Chart1
        set  # Chart1.top10_company_exposure = CT.top10_company_exposure
        From
         # Chart1 C1
        INNER JOIN  # Company_Top10 CT ON C1.unique_key = CT.unique_key

        update  # Chart1 set degree_of_control_sector_normalized = (degree_of_control_sector/(select max(degree_of_control_sector) from #Chart1))*100
        update  # Chart1 set degree_of_control_company_normalized = (degree_of_control_company/(select max(degree_of_control_sector) from #Chart1))*100

    - - select * from  # Chart1 order by degree_of_control_sector desc
    delete t_chart_top10_exposures where sector_id = @SectorID and year = @Year and company_name = @company_name

    insert into t_chart_top10_exposures( sector_id, year, company_name, top10_sector_exposure , degree_of_control_sector , degree_of_control_company ,
                                        degree_of_control_sector_normalized , degree_of_control_company_normalized , top10_company_exposure, added_dt, added_by,modify_dt, modify_by )
    SELECT  @ SectorID, @ Year,@company_name, top10_sector_exposure ,degree_of_control_sector ,degree_of_control_company ,degree_of_control_sector_normalized ,
    degree_of_control_company_normalized,
                                        top10_company_exposure, CURRENT_TIMESTAMP, 'Mohan Hanumantha', CURRENT_TIMESTAMP, 'Mohan Hanumantha' from  # Chart1

        select * from t_chart_top10_exposures order by degree_of_control_sector desc


    END


    GO
