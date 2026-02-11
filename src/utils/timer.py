import time

class BlockTimer:
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        self.total_time = self.end_time - self.start_time
        print(f"Block Timer: {self.total_time:.4f} seconds")
        
        #self note: return None NOT self because self = truthy
        #truth being returned for __exit__ = "Oh, the programmer handled the error. I'll hide it and keep going."
        return None 


    