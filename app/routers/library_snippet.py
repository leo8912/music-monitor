@router.delete("/source/{source_db_id}")
async def delete_source(
    source_db_id: int,
    delete_file: bool = Query(True, description="Whether to delete the physical file"),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Delete a specific source (e.g., a specific local file).
    If it's a local source, optionally delete the physical file.
    """
    try:
        # 1. Fetch the source
        stmt = select(SongSource).where(SongSource.id == source_db_id)
        result = await db.execute(stmt)
        source = result.scalar_one_or_none()
        
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
            
        file_path_to_delete = None
        if source.source == 'local' and delete_file and source.url:
             file_path_to_delete = source.url
             
        # 2. Delete from DB
        await db.delete(source)
        await db.commit()
        
        # 3. Delete physical file if requested
        deleted_file = False
        if file_path_to_delete and os.path.exists(file_path_to_delete):
            try:
                os.remove(file_path_to_delete)
                deleted_file = True
                logger.info(f"🗑️ Deleted physical file: {file_path_to_delete}")
            except Exception as e:
                logger.error(f"❌ Failed to delete file {file_path_to_delete}: {e}")
                # We don't rollback DB transaction because the user purpose is to remove it from library primarily
                # But we should probably warn? 
                
        return {
            "success": True, 
            "message": "Source deleted", 
            "file_deleted": deleted_file
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Delete source failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
