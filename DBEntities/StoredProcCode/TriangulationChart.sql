SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- Create the stored procedure in the specified schema
CREATE PROCEDURE [dbo].[sp_load_triangulation_chart_data]
@company_name VARCHAR(100),
@SectorID INTEGER,
@Year INTEGER
AS
BEGIN

    create table #triangulation_scores(
        sector_id int not null, 
        year int not null,
        sector_exposure_path_name varchar(100),
        sector_exposure_internalization_score FLOAT NULL,
        sector_exposure_mitigation_score FLOAT NULL,
        sector_internalization_mitigation_score FLOAT NULL,
        sector_exposure_internalization_score_normalized FLOAT NULL,
        sector_exposure_mitigation_score_normalized FLOAT NULL,
        sector_internalization_mitigation_score_normalized FLOAT NULL,
        company_name varchar(100)  NULL,
        company_exposure_internalization_score FLOAT NULL,
        company_exposure_mitigation_score FLOAT NULL,
        company_internalization_mitigation_score FLOAT NULL,
        company_exposure_internalization_score_normalized FLOAT NULL,
        company_exposure_mitigation_score_normalized FLOAT NULL,
        company_internalization_mitigation_score_normalized FLOAT NULL
    )

    create table #Exposure_Internalization(
        sector_id int,
        year int,
        sector_exposure_path_name varchar(100),
        exposure_internalization_score FLOAT
    )
    create table #Exposure_Mitigation(
        sector_id int,
        year int,
        sector_exposure_path_name varchar(100),
        exposure_mitigation_score FLOAT
    )
    create table #Internalization_Mitigation(
        sector_id int,
        year int,
        sector_exposure_path_name varchar(100),
        internalization_mitigation_score FLOAT
    )

    create table #Exposure_Mitigation_Company(
            exposure_path_name varchar(100),
            exposure_mitigation_score FLOAT
        )

    create table #Exposure_Internalization_Company(
            exposure_path_name varchar(100),
            exposure_internalization_score FLOAT
        )

        create table #Internalization_Mitigation_Company(
            exposure_path_name varchar(100),
            internalization_mitigation_score FLOAT
        )



    TRUNCATE TABLE #triangulation_scores

--- Update Sector Scores

    insert into #Internalization_Mitigation
        select  sector_id,year, exposure_path_name, avg(score) score from t_sector_exp_int_mitigation_insights
        where year = @Year and sector_id = @SectorID
        group by sector_id, year, exposure_path_name
        order by year,  score desc,exposure_path_name

    -- select * from #Internalization_Mitigation order by year,  sector_exposure_path_name

    insert into #Exposure_Mitigation
        select  sector_id,year, exposure_path_name, avg(score) score from t_sector_exp_mitigation_insights
        where year = @Year and sector_id = @SectorID
        group by sector_id, year, exposure_path_name        
        order by year,  score desc,exposure_path_name
    -- select * from #Exposure_Mitigation order by year,  sector_exposure_path_name

    insert into #Exposure_Internalization
        select  sector_id, year, exposure_path_name, avg(score) score from t_sector_exp_int_insights
        where year = @Year and sector_id = @SectorID
        group by sector_id, year, exposure_path_name
        order by year,  score desc,exposure_path_name
    -- select * from #Exposure_Internalization order by year,  sector_exposure_path_name

    insert into #triangulation_scores( sector_id, year,sector_exposure_path_name, sector_internalization_mitigation_score, company_name)
    select sector_id, year, sector_exposure_path_name, internalization_mitigation_score, @company_name
    from  #Internalization_Mitigation order by year,  sector_exposure_path_name
   
    update #triangulation_scores 
    set sector_exposure_mitigation_score = EM.exposure_mitigation_score
    from #triangulation_scores T1 
        INNER JOIN #Exposure_Mitigation EM ON T1.sector_exposure_path_name = EM.sector_exposure_path_name and EM.sector_id = T1.sector_id and EM.[year] = T1.[year]

    update #triangulation_scores 
    set sector_exposure_internalization_score = EI.exposure_internalization_score
    from #triangulation_scores T1 
        INNER JOIN #Exposure_Internalization EI ON T1.sector_exposure_path_name = EI.sector_exposure_path_name and EI.sector_id = T1.sector_id and EI.[year] = T1.[year]

    update #triangulation_scores set sector_exposure_internalization_score_normalized = (sector_exposure_internalization_score/(select max(sector_exposure_internalization_score) from #triangulation_scores))*100
    update #triangulation_scores set sector_exposure_mitigation_score_normalized = (sector_exposure_mitigation_score/(select max(sector_exposure_mitigation_score) from #triangulation_scores))*100
    update #triangulation_scores set sector_internalization_mitigation_score_normalized = (sector_internalization_mitigation_score/(select max(sector_internalization_mitigation_score) from #triangulation_scores))*100

--- Update Company Scores
    insert into #Exposure_Mitigation_Company
      select exp.exposure_path_name, avg(score)
        from t_mitigation_exp_insights insights
        inner join t_exposure_pathway exp on exp.exposure_path_id = insights.exposure_path_id
        INNER join t_document doc on doc.document_id = insights.document_id and doc.company_name = @company_name
        where insights.year =@Year and insights.sector_id = @SectorID
        group by exp.exposure_path_name
    
    -- select * from #Exposure_Mitigation_Company
    update #triangulation_scores 
    set company_exposure_mitigation_score = EMC.exposure_mitigation_score, company_name = @company_name
    from #triangulation_scores T1 
        INNER JOIN #Exposure_Mitigation_Company EMC ON T1.sector_exposure_path_name = EMC.exposure_path_name

    insert into #Exposure_Internalization_Company
      select exp.exposure_path_name, avg(score) 
        from t_exp_int_insights insights
        inner join t_exposure_pathway exp on exp.exposure_path_id = insights.exposure_path_id
        INNER join t_document doc on doc.document_id = insights.document_id and doc.company_name =@company_name
        where insights.year =@Year
        group by exp.exposure_path_name

    -- select * from #Exposure_Internalization_Company

    update #triangulation_scores 
    set company_exposure_internalization_score = EIC.exposure_internalization_score
    from #triangulation_scores T1 
        INNER JOIN #Exposure_Internalization_Company EIC ON T1.sector_exposure_path_name = EIC.exposure_path_name

    insert into #Internalization_Mitigation_Company
        select exp.exposure_path_name, avg(score) 
            from t_mitigation_exp_int_insights insights
            inner join t_exposure_pathway exp on exp.exposure_path_id = insights.exposure_path_id
            INNER join t_document doc on doc.document_id = insights.document_id and doc.company_name =@company_name
            where insights.year =@Year
            group by exp.exposure_path_name
    -- select * from #Internalization_Mitigation_Company

    update #triangulation_scores 
    set company_internalization_mitigation_score = IMC.internalization_mitigation_score
    from #triangulation_scores T1 
        INNER JOIN #Internalization_Mitigation_Company IMC ON T1.sector_exposure_path_name = IMC.exposure_path_name

    update #triangulation_scores set company_exposure_mitigation_score_normalized = (company_exposure_mitigation_score/(select max(sector_exposure_mitigation_score) from #triangulation_scores))*100
    update #triangulation_scores set company_exposure_internalization_score_normalized = (company_exposure_internalization_score/(select max(sector_exposure_internalization_score) from #triangulation_scores))*100
    update #triangulation_scores set company_internalization_mitigation_score_normalized = (company_internalization_mitigation_score/(select max(sector_internalization_mitigation_score) from #triangulation_scores))*100

    delete t_chart_triangulation where sector_id = @SectorID and year = @Year and company_name = @company_name

    insert into t_chart_triangulation(sector_id,  year, sector_exposure_path_name,sector_exposure_internalization_score , sector_exposure_mitigation_score  ,
                                     sector_internalization_mitigation_score,sector_exposure_internalization_score_normalized  ,sector_exposure_mitigation_score_normalized  ,
                                     sector_internalization_mitigation_score_normalized,company_name,company_exposure_internalization_score,company_exposure_mitigation_score  ,
                                     company_internalization_mitigation_score  ,company_exposure_internalization_score_normalized  ,company_exposure_mitigation_score_normalized  ,
                                     company_internalization_mitigation_score_normalized, added_dt, added_by,modify_dt, modify_by)
    SELECT sector_id,  year, sector_exposure_path_name,sector_exposure_internalization_score , sector_exposure_mitigation_score  ,
                                     sector_internalization_mitigation_score,sector_exposure_internalization_score_normalized  ,sector_exposure_mitigation_score_normalized  ,
                                     sector_internalization_mitigation_score_normalized,company_name,company_exposure_internalization_score,company_exposure_mitigation_score  ,
                                     company_internalization_mitigation_score  ,company_exposure_internalization_score_normalized  ,company_exposure_mitigation_score_normalized  ,
                                     company_internalization_mitigation_score_normalized , CURRENT_TIMESTAMP,'Mohan Hanumantha', CURRENT_TIMESTAMP, 'Mohan Hanumantha' from 
    #triangulation_scores

    select * from t_chart_triangulation order by year, sector_exposure_path_name
END
